# ============================================================
#  ONLINE OKEY OYUNU — main.py (Gelişmiş Test Başlatıcı)
#  Modern ve şık bir arayüz ile çoklu istemci yönetimi.
# ============================================================

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys
import subprocess
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton,
                             QLabel, QFrame, QHBoxLayout, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QFont, QIcon

# Config'den başlığı çekelim, yoksa varsayılan kullanalım
try:
    from config import WINDOW_TITLE
except ImportError:
    WINDOW_TITLE = "Online Okey"


class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{WINDOW_TITLE} - Test Merkezi")
        self.setFixedSize(500, 350)
        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._init_ui()

    def _init_ui(self):
        # Ana Arkaplan ve Stil
        self.setObjectName("MainWindow")
        self.setStyleSheet("""
            #MainWindow {
                background-color: #1a3020; /* Koyu Okey Masası Yeşili */
            }

            #LauncherCard {
                background-color: rgba(45, 90, 66, 180);
                border: 2px solid #3a7355;
                border-radius: 20px;
            }

            #TitleLabel {
                color: #f1c40f; /* Altın Sarısı */
                font-family: 'Segoe UI', Arial;
                font-size: 28px;
                font-weight: bold;
                margin-bottom: 5px;
            }

            #SubtitleLabel {
                color: #ecf0f1;
                font-size: 13px;
                margin-bottom: 20px;
            }

            #ClientBtn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f1c40f, stop:1 #d4ac0d);
                border: none;
                border-radius: 10px;
                color: #1a3020;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
                min-width: 200px;
            }

            #ClientBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f4d03f, stop:1 #f1c40f);
            }

            #ClientBtn:pressed {
                background: #b7950b;
                padding-top: 14px;
            }

            #InfoBox {
                background-color: rgba(0, 0, 0, 60);
                border-radius: 10px;
                padding: 10px;
                color: #aeb6bf;
                font-size: 11px;
            }
        """)

        # Layoutlar
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Merkez Kartı
        self.card = QFrame()
        self.card.setObjectName("LauncherCard")

        # Gölge Efekti
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setAlignment(Qt.AlignCenter)
        card_layout.setSpacing(10)

        # Başlık Bölümü
        title = QLabel("ONLINE OKEY")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Geliştirici Test Arayüzü")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignCenter)

        # Buton Bölümü
        self.btn_client = QPushButton("🎮  YENİ OYUNCU EKLE")
        self.btn_client.setObjectName("ClientBtn")
        self.btn_client.setCursor(Qt.PointingHandCursor)
        self.btn_client.clicked.connect(self.spawn_client)

        # Alt Bilgi Kutusu
        info_box = QLabel(
            "İpucu: Önce 'server.py' dosyasını başlatın.\n"
            "Ardından her tıklamada yeni bir pencere açılır."
        )
        info_box.setObjectName("InfoBox")
        info_box.setAlignment(Qt.AlignCenter)

        # Yerleştirme
        card_layout.addStretch()
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(20)
        card_layout.addWidget(self.btn_client)
        card_layout.addSpacing(20)
        card_layout.addWidget(info_box)
        card_layout.addStretch()

        main_layout.addWidget(self.card)

    def spawn_client(self):
        # Bağımsız bir process olarak client.py'yi çalıştır
        try:
            subprocess.Popen([sys.executable, "client.py"])
        except Exception as e:
            print(f"Hata: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Modern font ayarı
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    launcher = Launcher()
    launcher.show()
    sys.exit(app.exec_())