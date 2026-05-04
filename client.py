# ============================================================
#  ONLINE OKEY OYUNU — client.py (Final Sürüm)
#  Kuşbakışı Masa, Ahşap İstaka Düzeni ve Responsive Tasarım
# ============================================================
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import os
import socket
import json

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QTextEdit,
    QScrollArea, QFrame, QStackedWidget, QMessageBox, QSizePolicy,
    QSpacerItem, QProgressBar, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QMimeData
from PyQt5.QtGui import (QPainter, QColor, QBrush, QPen, QFont,
                         QLinearGradient, QCursor, QDrag, QPixmap)

from config import HOST, PORT, BUFFER_SIZE, WINDOW_TITLE, WINDOW_WIDTH, WINDOW_HEIGHT, MIN_WIDTH, MIN_HEIGHT
from protocol import (MsgType, parse,
                      build_join, build_draw, build_draw_discard,
                      build_discard, build_win, build_chat, tile_to_label)

# ─────────────────────────────────────────────────────────────
#  Renk Tanımları
# ─────────────────────────────────────────────────────────────
TILE_FACE_COLORS = {
    "kirmizi": ("#C0392B", "#E74C3C", "#FF6B6B"),
    "sari": ("#9A6F00", "#D4A017", "#F0C030"),
    "mavi": ("#154360", "#1A5276", "#2E86C1"),
    "siyah": ("#1C2833", "#2C3E50", "#4A6074"),
    "joker": ("#6C3483", "#8E44AD", "#BB8FCC"),
}


# ─────────────────────────────────────────────────────────────
#  Ağ İş Parçacığı
# ─────────────────────────────────────────────────────────────
class NetworkThread(QThread):
    message_received = pyqtSignal(dict)
    connection_lost = pyqtSignal(str)

    def __init__(self, host: str, port: int):
        super().__init__()
        self.host = host
        self.port = port
        self.sock = None
        self._alive = True
        self.buffer = ""

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)
        except Exception as e:
            self.connection_lost.emit(str(e))
            return

        while self._alive:
            try:
                chunk = self.sock.recv(BUFFER_SIZE).decode("utf-8", errors="ignore")
                if not chunk:
                    self.connection_lost.emit("Sunucu bağlantısı kapandı.")
                    break
                self.buffer += chunk
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        msg = parse(line)
                        if msg:
                            self.message_received.emit(msg)
            except Exception as e:
                if self._alive:
                    self.connection_lost.emit(str(e))
                break

    def send(self, data: str):
        if self.sock:
            try:
                self.sock.sendall((data + "\n").encode("utf-8"))
            except Exception:
                pass

    def stop(self):
        self._alive = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────
#  Okey Taşı Widget'ı (Sürükle-Bırak Destekli)
# ─────────────────────────────────────────────────────────────
class TileButton(QPushButton):
    def __init__(self, tile_dict: dict | None = None, clickable: bool = True, parent=None):
        super().__init__(parent)
        self.tile_dict = tile_dict
        self._selected = False
        self.clickable = clickable

        # Responsive olması için sabit boyutları kaldırdık
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFlat(True)
        self.setObjectName("tileBtn")
        if not clickable:
            self.setEnabled(False)
        self.setCursor(QCursor(Qt.PointingHandCursor) if clickable else QCursor(Qt.ArrowCursor))

        self.drag_start_pos = None

    def set_tile(self, tile_dict: dict | None):
        self.tile_dict = tile_dict
        self.update()

    @property
    def selected(self):
        return self._selected

    @selected.setter
    def selected(self, val: bool):
        self._selected = val
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.clickable:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or not self.clickable or not self.drag_start_pos:
            return

        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()

        drag_data = {
            "tile": self.tile_dict,
            "src_row": getattr(self, 'row', -1),
            "src_col": getattr(self, 'col', -1)
        }
        mime_data.setText(json.dumps(drag_data))
        drag.setMimeData(mime_data)

        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())

        self.hide()
        drop_action = drag.exec_(Qt.MoveAction)

        # Üst üste binmeleri ve hayalet taşları engellemek için düzeltme
        if drop_action == Qt.IgnoreAction:
            self.show()
        else:
            self.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        rx, ry = max(3, int(w * 0.12)), max(3, int(w * 0.12))  # Dinamik köşe yuvarlama

        if not self._selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(0, 0, 0, 60)))
            painter.drawRoundedRect(4, 6, w - 6, h - 4, rx, ry)

        if self.tile_dict is None:
            grad = QLinearGradient(0, 0, 0, h)
            grad.setColorAt(0, QColor("#2E4A38"))
            grad.setColorAt(1, QColor("#1E3228"))
            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor("#3A5A42"), 2))
            painter.drawRoundedRect(2, 2, w - 4, h - 4, rx, ry)
            painter.end()
            return

        color = self.tile_dict.get("color", "siyah")
        number = self.tile_dict.get("number", 0)
        is_joker = self.tile_dict.get("is_fake_joker", False)
        dark, mid, light = TILE_FACE_COLORS.get(color, ("#333", "#555", "#888"))

        if self._selected:
            painter.setBrush(QBrush(QColor("#F0C830")))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(0, 0, w, h, rx + 2, rx + 2)

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor("#FDFAF2"))
        grad.setColorAt(1, QColor("#EDE8DC"))
        painter.setBrush(QBrush(grad))
        border_color = QColor("#F0C830") if self._selected else QColor(dark)
        border_width = 3 if self._selected else 2
        painter.setPen(QPen(border_color, border_width))
        margin = max(1, int(w * 0.05))
        painter.drawRoundedRect(margin, margin, w - margin * 2, h - margin * 2, rx - 1, rx - 1)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(mid)))
        painter.drawRoundedRect(margin + 1, margin + 1, w - margin * 2 - 2, max(4, int(h * 0.1)), 3, 3)
        painter.drawRect(margin + 1, margin + int(h * 0.06), w - margin * 2 - 2, max(2, int(h * 0.05)))

        if is_joker:
            painter.setPen(QPen(QColor(mid)))
            f = QFont("Segoe UI", max(8, int(h * 0.2)), QFont.Black)
            painter.setFont(f)
            painter.drawText(0, 0, w, h, Qt.AlignCenter, "OK")

            painter.setBrush(QBrush(QColor(light)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(w // 2 - int(w * 0.08), h - int(h * 0.2), int(w * 0.15), int(w * 0.15))
        else:
            painter.setPen(QPen(QColor(dark)))
            num_str = str(number)
            font_size = max(10, int(h * 0.35)) if number < 10 else max(8, int(h * 0.28))
            f = QFont("Arial Black", font_size, QFont.Black)
            painter.setFont(f)
            painter.drawText(2, int(h * 0.1), w - 4, h - int(h * 0.2), Qt.AlignCenter, num_str)

            painter.setBrush(QBrush(QColor(mid)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(w // 2 - int(w * 0.1), h - int(h * 0.2), int(w * 0.2), int(w * 0.2))

        painter.end()


# ─────────────────────────────────────────────────────────────
#  İstaka Yuvası (RackSlot)
# ─────────────────────────────────────────────────────────────
class RackSlot(QWidget):
    tile_dropped = pyqtSignal(dict, int, int)

    def __init__(self, row: int, col: int, parent=None):
        super().__init__(parent)
        self.row = row
        self.col = col
        self.setObjectName("rackSlot")
        # Responsive olması için sabit boyutları kaldırdık
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAcceptDrops(True)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.current_tile: TileButton = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        data_str = event.mimeData().text()
        try:
            data_dict = json.loads(data_str)
            self.tile_dropped.emit(data_dict, self.row, self.col)
            event.acceptProposedAction()
        except json.JSONDecodeError:
            pass

    def set_tile(self, tile_btn: TileButton):
        self.clear()
        self.current_tile = tile_btn
        tile_btn.row = self.row
        tile_btn.col = self.col
        self.layout.addWidget(tile_btn)
        tile_btn.show()

    def clear(self):
        if self.current_tile:
            self.layout.removeWidget(self.current_tile)
            self.current_tile.deleteLater()
            self.current_tile = None

    def get_tile_dict(self):
        if self.current_tile:
            return self.current_tile.tile_dict
        return None


# ─────────────────────────────────────────────────────────────
#  GİRİŞ EKRANI (LoginWidget)
# ─────────────────────────────────────────────────────────────
class LoginWidget(QWidget):
    connect_requested = pyqtSignal(str, str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loginPage")

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        self.card = QFrame()
        self.card.setObjectName("loginCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setSpacing(16)
        card_layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("ONLINE OKEY")
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Arkadaşlarınla oynamaya hazır mısın?")
        subtitle.setObjectName("loginSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(subtitle)

        card_layout.addWidget(QLabel("Oyuncu Adı"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Adını gir...")
        self.name_input.setObjectName("loginInput")
        card_layout.addWidget(self.name_input)

        card_layout.addWidget(QLabel("Sunucu IP"))
        self.ip_input = QLineEdit(str(HOST))
        self.ip_input.setObjectName("loginInput")
        card_layout.addWidget(self.ip_input)

        card_layout.addWidget(QLabel("Port"))
        self.port_input = QLineEdit(str(PORT))
        self.port_input.setObjectName("loginInput")
        card_layout.addWidget(self.port_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.error_label)

        self.connect_btn = QPushButton("OYUNA BAĞLAN")
        self.connect_btn.setObjectName("primaryBtn")
        self.connect_btn.clicked.connect(self._on_connect)
        card_layout.addWidget(self.connect_btn)

        main_layout.addWidget(self.card)
        for label in self.findChildren(QLabel):
            label.setStyleSheet("background-color: transparent;")

    def _on_connect(self):
        name = self.name_input.text().strip()
        host = self.ip_input.text().strip()
        port_str = self.port_input.text().strip()

        if not name:
            self.show_error("Oyuncu adı gerekli.")
            return
        if not host:
            self.show_error("Sunucu adresi gerekli.")
            return
        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            self.show_error("Geçerli bir port numarası girin (1-65535).")
            return

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Bağlanıyor...")
        self.error_label.clear()
        self.connect_requested.emit(name, host, port)

    def show_error(self, msg: str):
        self.error_label.setText(msg)
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("OYUNA BAĞLAN")

    def reset(self):
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("OYUNA BAĞLAN")
        self.error_label.clear()


# ─────────────────────────────────────────────────────────────
#  BEKLEME ODASI (WaitingWidget)
# ─────────────────────────────────────────────────────────────
class WaitingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("waitingPage")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("OYUNCULAR BEKLENİYOR...")
        title.setObjectName("loginTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #D0B060;")

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("playerList")
        self.list_widget.setMaximumWidth(400)
        self.list_widget.setMinimumHeight(200)
        self.list_widget.setStyleSheet("font-size: 16px;")

        self.cancel_btn = QPushButton("BEKLEMEKTEN VAZGEÇ")
        self.cancel_btn.setObjectName("secondaryBtn")
        self.cancel_btn.clicked.connect(self._cancel)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #C8B890; font-size: 14px;")

        layout.addWidget(title)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.info_label)
        layout.addWidget(self.cancel_btn)

    def update_players(self, players, count, max_count):
        self.list_widget.clear()
        for name in players:
            item = QListWidgetItem(f"♦ {name}")
            item.setForeground(QColor("#E0E0D0"))
            self.list_widget.addItem(item)
        self.info_label.setText(f"{count}/{max_count} oyuncu")

    def _cancel(self):
        QApplication.quit()

    # ─────────────────────────────────────────────────────────────


#  Oyun Ekranı (GameWidget)
# ─────────────────────────────────────────────────────────────
class GameWidget(QWidget):
    action_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gamePage")
        self.my_id = -1
        self.current_turn_id = -1
        self.has_drawn = False
        self.selected_tile = None
        self.rack_slots = []
        self._build_ui()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        board_container = QWidget()
        board_container.setObjectName("gameBoardArea")
        board_layout = QGridLayout(board_container)
        board_layout.setSpacing(15)

        self.top_opponent = self._build_opponent_view("horizontal")
        self.left_opponent = self._build_opponent_view("vertical")
        self.right_opponent = self._build_opponent_view("vertical")

        board_layout.addWidget(self.top_opponent, 0, 1, Qt.AlignCenter)
        board_layout.addWidget(self.left_opponent, 1, 0, Qt.AlignCenter)
        board_layout.addWidget(self.right_opponent, 1, 2, Qt.AlignCenter)

        board_layout.addWidget(self._build_center_table(), 1, 1, Qt.AlignCenter)

        bottom_wrap = QHBoxLayout()
        bottom_wrap.setSpacing(10)

        left_action_box = QVBoxLayout()
        left_action_box.addStretch()
        self.left_discard = TileButton(clickable=False)
        self.draw_discard_btn = QPushButton("SOL\nATIKTAN AL")
        self.draw_discard_btn.setObjectName("secondaryBtn")
        self.draw_discard_btn.clicked.connect(
            lambda: self.action_requested.emit(json.dumps({"type": MsgType.DRAW_DISCARD})))
        left_action_box.addWidget(self.left_discard, 0, Qt.AlignCenter)
        left_action_box.addWidget(self.draw_discard_btn, 0, Qt.AlignCenter)

        self.my_rack_widget = self._build_my_rack()

        right_action_box = QVBoxLayout()
        right_action_box.addStretch()
        self.my_discard = TileButton(clickable=False)
        self.discard_btn = QPushButton("SEÇİLİ TAŞI\nSAĞA AT")
        self.discard_btn.setStyleSheet(
            "background-color: #8B2020; color: white; font-weight: bold; border-radius: 6px; padding: 10px;")
        self.discard_btn.clicked.connect(self._on_discard)
        right_action_box.addWidget(self.my_discard, 0, Qt.AlignCenter)
        right_action_box.addWidget(self.discard_btn, 0, Qt.AlignCenter)

        bottom_wrap.addLayout(left_action_box)
        bottom_wrap.addWidget(self.my_rack_widget, 1)
        bottom_wrap.addLayout(right_action_box)

        board_layout.addLayout(bottom_wrap, 2, 0, 1, 3)

        board_layout.setRowStretch(1, 1)
        board_layout.setColumnStretch(1, 1)
        main_layout.addWidget(board_container, 4)

        right_panel = QVBoxLayout()
        right_panel.addWidget(self._build_info_panel())
        right_panel.addWidget(self._build_chat_panel())
        main_layout.addLayout(right_panel, 1)

    # TAM EKRAN (RESPONSIVE) DÜZENLEMESİ İÇİN RESIZE EVENT
    def resizeEvent(self, event):
        super().resizeEvent(event)

        base_w = self.width()
        new_slot_w = max(45, int(base_w * 0.045))
        new_slot_h = int(new_slot_w * 1.45)

        new_tile_w = new_slot_w - 2
        new_tile_h = new_slot_h - 2

        for r in range(2):
            for c in range(11):
                self.rack_slots[r][c].setFixedSize(new_slot_w, new_slot_h)

        if hasattr(self, 'left_discard'):
            self.left_discard.setFixedSize(new_tile_w, new_tile_h)
            self.my_discard.setFixedSize(new_tile_w, new_tile_h)
            self.indicator_btn.setFixedSize(new_tile_w, new_tile_h)

        if hasattr(self, 'draw_pile_btn'):
            self.draw_pile_btn.setFixedSize(int(new_slot_w * 1.8), int(new_slot_h * 1.1))

    def _build_opponent_view(self, orientation: str) -> QWidget:
        w = QWidget()
        w.setObjectName("opponentCard")
        layout = QHBoxLayout(w) if orientation == "horizontal" else QVBoxLayout(w)

        w._name_lbl = QLabel("—")
        w._name_lbl.setObjectName("playerName")
        w._name_lbl.setAlignment(Qt.AlignCenter)

        w._count_lbl = QLabel("0 taş")
        w._count_lbl.setObjectName("tileCount")
        w._count_lbl.setAlignment(Qt.AlignCenter)

        info_lay = QVBoxLayout()
        info_lay.addWidget(w._name_lbl)
        info_lay.addWidget(w._count_lbl)
        layout.addLayout(info_lay)

        w._tiles_container = QWidget()
        w._tiles_container.setObjectName("opponentTileBack")
        w._tiles_container.setFixedSize(60, 40) if orientation == "horizontal" else w._tiles_container.setFixedSize(40,
                                                                                                                    60)
        layout.addWidget(w._tiles_container)

        return w

    def _build_center_table(self) -> QWidget:
        center = QWidget()
        layout = QGridLayout(center)
        layout.setSpacing(15)

        mid_box = QWidget()
        mid_lay = QHBoxLayout(mid_box)

        # GENİŞLETİLMİŞ BUTON
        self.draw_pile_btn = QPushButton("ORTADAN\nÇEK (106)")
        self.draw_pile_btn.setFixedSize(120, 90)
        self.draw_pile_btn.setStyleSheet(
            "background-color: #1A3020; border: 2px solid #C9A84C; color: #E8DCC8; font-weight: bold; border-radius: 6px;")
        self.draw_pile_btn.clicked.connect(lambda: self.action_requested.emit(json.dumps({"type": MsgType.DRAW})))

        self.indicator_btn = TileButton(clickable=False)

        mid_lay.addWidget(self.draw_pile_btn)
        mid_lay.addWidget(self.indicator_btn)
        layout.addWidget(mid_box, 0, 0, Qt.AlignCenter)

        return center

    def _build_my_rack(self) -> QWidget:
        rack = QWidget()
        rack.setObjectName("myRackWidget")

        # AHŞAP İSTAKA GÖRÜNÜMÜ
        rack.setStyleSheet("""
            #myRackWidget {
                background-color: #613C24; 
                border: 4px solid #3A2212;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(rack)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(4)

        self.rack_slots = [[None for _ in range(11)] for _ in range(2)]

        row0_lay = QHBoxLayout()
        row0_lay.setSpacing(4)
        for c in range(11):
            slot = RackSlot(0, c)
            slot.tile_dropped.connect(self._on_tile_dropped)
            row0_lay.addWidget(slot)
            self.rack_slots[0][c] = slot
        layout.addLayout(row0_lay)

        # 3 BOYUTLU OYUK/KAT ÇİZGİSİ
        fold_line = QFrame()
        fold_line.setFrameShape(QFrame.HLine)
        fold_line.setStyleSheet("""
            border-top: 5px solid #2B170B;    
            border-bottom: 2px solid #825435; 
            margin: 2px 5px;
        """)
        layout.addWidget(fold_line)

        row1_lay = QHBoxLayout()
        row1_lay.setSpacing(4)
        for c in range(11):
            slot = RackSlot(1, c)
            slot.tile_dropped.connect(self._on_tile_dropped)
            row1_lay.addWidget(slot)
            self.rack_slots[1][c] = slot
        layout.addLayout(row1_lay)

        btn_lay = QHBoxLayout()
        self.selected_info = QLabel("Taş seçilmedi")
        self.selected_info.setObjectName("infoLabel")

        self.win_btn = QPushButton("⭐ OKEY YAPIYORUM ⭐")
        self.win_btn.setObjectName("primaryBtn")
        self.win_btn.setFixedSize(220, 36)
        self.win_btn.clicked.connect(lambda: self.action_requested.emit(json.dumps({"type": MsgType.WIN})))

        btn_lay.addWidget(self.selected_info)
        btn_lay.addStretch()
        btn_lay.addWidget(self.win_btn)
        btn_lay.addStretch()
        layout.addLayout(btn_lay)

        return rack

    def _build_info_panel(self) -> QWidget:
        w = QWidget()
        w.setObjectName("sidePanel")
        lay = QVBoxLayout(w)

        self.turn_banner = QLabel("Sıra Bekleniyor...")
        self.turn_banner.setObjectName("turnBanner")
        self.turn_banner.setAlignment(Qt.AlignCenter)

        self.turn_timer = QProgressBar()
        self.turn_timer.setObjectName("turnTimer")
        self.turn_timer.setRange(0, 60)
        self.turn_timer.setValue(60)
        self.turn_timer.setTextVisible(False)
        self.turn_timer.setFixedHeight(10)

        self.okey_label = QLabel("Okey: —")
        self.okey_label.setObjectName("okeyLabel")
        self.okey_label.setAlignment(Qt.AlignCenter)

        lay.addWidget(self.turn_banner)
        lay.addWidget(self.turn_timer)
        lay.addSpacing(10)
        lay.addWidget(self.okey_label)
        lay.addStretch()
        return w

    def _build_chat_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("chatPanel")
        layout = QVBoxLayout(panel)

        title = QLabel("SOHBET")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display, 1)

        inp_row = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setObjectName("chatInput")
        self.chat_input.returnPressed.connect(self._on_send_chat)

        send_btn = QPushButton("➤")
        send_btn.setObjectName("sendBtn")
        send_btn.clicked.connect(self._on_send_chat)

        inp_row.addWidget(self.chat_input)
        inp_row.addWidget(send_btn)
        layout.addLayout(inp_row)
        return panel

    def update_state(self, state: dict):
        self.my_id = state.get("my_id", -1)
        self.current_turn_id = state.get("current_turn_id", -1)
        self.has_drawn = state.get("has_drawn", False)
        is_my_turn = (self.my_id == self.current_turn_id)

        players = state.get("players", [])

        current_name = next((p["name"] for p in players if p["id"] == self.current_turn_id), "")
        if is_my_turn:
            self.turn_banner.setText("🟢 SİZİN SIRANIZ!")
            self.turn_banner.setProperty("myturn", True)
        else:
            self.turn_banner.setText(f"⏳ {current_name} oynuyor")
            self.turn_banner.setProperty("myturn", False)
        self.turn_banner.style().unpolish(self.turn_banner)
        self.turn_banner.style().polish(self.turn_banner)

        my_idx = next((i for i, p in enumerate(players) if p["id"] == self.my_id), 0)
        num_players = len(players)

        if num_players > 1:
            self._update_opponent_widget(self.right_opponent, players[(my_idx + 1) % num_players])
        if num_players > 2:
            self._update_opponent_widget(self.top_opponent, players[(my_idx + 2) % num_players])
        if num_players > 3:
            self._update_opponent_widget(self.left_opponent, players[(my_idx + 3) % num_players])

        pile_count = state.get("draw_pile_count", 0)
        self.draw_pile_btn.setText(f"ORTADAN\nÇEK ({pile_count})")

        if state.get("indicator_tile"):
            self.indicator_btn.set_tile(state.get("indicator_tile"))
        if state.get("okey_tile"):
            self.okey_label.setText(f"Okey: {tile_to_label(state['okey_tile'])}")

        self.left_discard.set_tile(state.get("left_discard_top"))
        self.my_discard.set_tile(state.get("my_discard_top"))

        server_hand = state.get("my_hand", [])
        if self._should_refresh_rack(server_hand):
            self._refresh_hand(server_hand)

        can_draw = is_my_turn and not self.has_drawn
        can_discard = is_my_turn and self.has_drawn

        self.draw_pile_btn.setEnabled(can_draw and pile_count > 0)
        self.draw_discard_btn.setEnabled(can_draw and state.get("left_discard_top") is not None)
        self.discard_btn.setEnabled(can_discard and self.selected_tile is not None)
        self.win_btn.setEnabled(can_discard)

    def _update_opponent_widget(self, widget: QWidget, p_data: dict):
        active = (p_data["id"] == self.current_turn_id)
        widget._name_lbl.setText(p_data["name"])
        widget._count_lbl.setText(f"{p_data['tile_count']} taş")
        widget.setProperty("active", active)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    # KUSURSUZ TAŞ TAKASI MANTIĞI
    def _on_tile_dropped(self, data_dict: dict, dest_row: int, dest_col: int):
        tile_dict = data_dict.get("tile")
        src_row = data_dict.get("src_row", -1)
        src_col = data_dict.get("src_col", -1)

        if src_row == dest_row and src_col == dest_col:
            return

        dest_slot = self.rack_slots[dest_row][dest_col]
        existing_tile_dict = dest_slot.get_tile_dict()

        if src_row != -1 and src_col != -1:
            self.rack_slots[src_row][src_col].clear()

        btn = TileButton(tile_dict=tile_dict)
        btn.clicked.connect(lambda checked, td=tile_dict, b=btn: self._on_tile_clicked(td, b))
        dest_slot.set_tile(btn)

        # Hedefte taş varsa kaynak yuvaya geri koy
        if existing_tile_dict and src_row != -1 and src_col != -1:
            swap_btn = TileButton(tile_dict=existing_tile_dict)
            swap_btn.clicked.connect(lambda checked, td=existing_tile_dict, b=swap_btn: self._on_tile_clicked(td, b))
            self.rack_slots[src_row][src_col].set_tile(swap_btn)

        self.selected_tile = None
        self.selected_info.setText("Taş seçilmedi")
        self.discard_btn.setEnabled(False)

    def _should_refresh_rack(self, server_hand: list[dict]) -> bool:
        rack_tiles = []
        for r in range(2):
            for c in range(11):
                td = self.rack_slots[r][c].get_tile_dict()
                if td:
                    rack_tiles.append(td)

        if len(rack_tiles) != len(server_hand):
            return True

        def sort_key(t):
            return (t.get("color"), t.get("number"), t.get("is_fake_joker"))

        sorted_rack = sorted(rack_tiles, key=sort_key)
        sorted_server = sorted(server_hand, key=sort_key)
        return sorted_rack != sorted_server

    def _refresh_hand(self, hand: list[dict]):
        for r in range(2):
            for c in range(11):
                self.rack_slots[r][c].clear()

        self.selected_tile = None
        self.selected_info.setText("Taş seçilmedi")

        sorted_hand = sorted(
            hand,
            key=lambda t: (
                ["kirmizi", "sari", "mavi", "siyah", "joker"].index(t.get("color", "siyah")),
                t.get("number", 0)
            )
        )

        idx = 0
        for r in range(2):
            for c in range(11):
                if idx < len(sorted_hand):
                    tile_dict = sorted_hand[idx]
                    btn = TileButton(tile_dict=tile_dict)
                    btn.clicked.connect(lambda checked, td=tile_dict, b=btn: self._on_tile_clicked(td, b))
                    self.rack_slots[r][c].set_tile(btn)
                    idx += 1

    def _on_tile_clicked(self, tile_dict: dict, btn: TileButton):
        for r in range(2):
            for c in range(11):
                if self.rack_slots[r][c].current_tile:
                    self.rack_slots[r][c].current_tile.selected = False

        if self.selected_tile == tile_dict:
            self.selected_tile = None
            self.selected_info.setText("Taş seçilmedi")
        else:
            self.selected_tile = tile_dict
            btn.selected = True
            self.selected_info.setText(f"Seçili: {tile_to_label(tile_dict)}")

        is_my_turn = (self.my_id == self.current_turn_id)
        can_discard = is_my_turn and self.has_drawn
        self.discard_btn.setEnabled(can_discard and self.selected_tile is not None)

    def _on_discard(self):
        if self.selected_tile:
            self.action_requested.emit(
                json.dumps({"type": MsgType.DISCARD, "tile": self.selected_tile},
                           ensure_ascii=False)
            )

    def _on_send_chat(self):
        text = self.chat_input.text().strip()
        if text:
            self.action_requested.emit(
                json.dumps({"type": MsgType.CHAT, "message": text}, ensure_ascii=False)
            )
            self.chat_input.clear()

    def append_chat(self, player_name: str, message: str, is_system: bool = False):
        if is_system:
            html = f'<span style="color:#7A8A7A; font-style:italic;">{message}</span>'
        else:
            html = (f'<span style="color:#C9A84C; font-weight:600;">{player_name}:</span> '
                    f'<span style="color:#C8B890;">{message}</span>')
        self.chat_display.append(html)
        sb = self.chat_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show_game_over(self, winner_name: str, is_me: bool):
        msg = f"🎉 {winner_name} OKEY YAPTI! 🎉" if not is_me else "🏆 TEBRİKLER! OKEY YAPTINIZ! 🏆"
        QMessageBox.information(self, "Oyun Bitti", msg)


# ─────────────────────────────────────────────────────────────
#  Ana Pencere
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)

        self.net_thread: NetworkThread | None = None
        self.player_name: str = ""

        self._load_style()
        self._build_stack()

    def _load_style(self):
        qss_path = os.path.join(os.path.dirname(__file__), "style.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _build_stack(self):
        self.stack = QStackedWidget()
        self.stack.setObjectName("centralWidget")

        self.login_widget = LoginWidget()
        self.waiting_widget = WaitingWidget()
        self.game_widget = GameWidget()

        self.stack.addWidget(self.login_widget)
        self.stack.addWidget(self.waiting_widget)
        self.stack.addWidget(self.game_widget)

        self.setCentralWidget(self.stack)
        self.stack.setCurrentIndex(0)

        self.login_widget.connect_requested.connect(self._on_connect_requested)
        self.game_widget.action_requested.connect(self._on_action)

    def _on_connect_requested(self, name: str, host: str, port: int):
        self.player_name = name
        self.net_thread = NetworkThread(host, port)
        self.net_thread.message_received.connect(self._on_message)
        self.net_thread.connection_lost.connect(self._on_connection_lost)
        self.net_thread.start()

        QTimer.singleShot(300, lambda: self.net_thread.send(build_join(name)))

    def _on_action(self, json_str: str):
        if self.net_thread:
            self.net_thread.send(json_str)

    def _on_message(self, msg: dict):
        msg_type = msg.get("type")

        if msg_type == MsgType.WAITING:
            self.stack.setCurrentIndex(1)
            self.waiting_widget.update_players(
                msg.get("players", []),
                msg.get("count", 0),
                msg.get("max", 4)
            )

        elif msg_type == MsgType.GAME_START:
            self.stack.setCurrentIndex(2)
            self.game_widget.append_chat("", msg.get("message", "Oyun başladı!"), is_system=True)
            starter = msg.get("starter_name", "")
            if starter:
                self.game_widget.append_chat("", f"İlk sıra: {starter}", is_system=True)

        elif msg_type == MsgType.GAME_STATE:
            self.game_widget.update_state(msg)

        elif msg_type == MsgType.GAME_OVER:
            winner_name = msg.get("winner_name", "?")
            winner_id = msg.get("winner_id", -1)
            is_me = (winner_id == self.game_widget.my_id)
            self.game_widget.append_chat("", msg.get("message", ""), is_system=True)
            QTimer.singleShot(300, lambda: self.game_widget.show_game_over(winner_name, is_me))

        elif msg_type == MsgType.CHAT_BROADCAST:
            self.game_widget.append_chat(
                msg.get("player_name", "?"),
                msg.get("message", "")
            )

        elif msg_type == MsgType.ERROR:
            error_msg = msg.get("message", "Bilinmeyen hata.")
            if self.stack.currentIndex() == 0:
                self.login_widget.show_error(error_msg)
            else:
                self.game_widget.append_chat("⚠️ Sistem", error_msg, is_system=True)

    def _on_connection_lost(self, reason: str):
        if self.stack.currentIndex() == 0:
            self.login_widget.show_error(f"Bağlantı hatası: {reason}")
            self.login_widget.reset()
        else:
            QMessageBox.critical(self, "Bağlantı Kesildi",
                                 f"Sunucu bağlantısı kesildi:\n{reason}")
            self.stack.setCurrentIndex(0)
            self.login_widget.reset()
        if self.net_thread:
            self.net_thread.stop()
            self.net_thread = None

    def closeEvent(self, event):
        if self.net_thread:
            self.net_thread.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()