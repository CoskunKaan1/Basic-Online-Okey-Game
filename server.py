# ============================================================
#  ONLINE OKEY OYUNU — server.py
#  Çalıştırma: python server.py
# ============================================================

import socket
import threading
import json
import logging
import sys
import time

# Windows terminali için UTF-8 zorlaması (Emoji çökmesini engeller)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from config      import HOST, PORT, MAX_PLAYERS, BUFFER_SIZE, TURN_TIMEOUT
from game_logic  import GameManager
from protocol    import MsgType, parse

# ── Loglama ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("OkeyServer")


# ─────────────────────────────────────────────────────────────
#  Sunucu
# ─────────────────────────────────────────────────────────────
class OkeyServer:
    def __init__(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.clients:      dict[int, socket.socket] = {}   # id → socket
        self.player_names: dict[int, str]           = {}   # id → isim
        self.lock  = threading.Lock()
        self.game  = GameManager()
        self.next_id = 1
        self._running = True

        # Zamanlayıcı değişkenleri
        self.last_action_time = 0
        self.timer_thread_started = False

    # ─── Başlatma ────────────────────────────────────────────
    def start(self):
        self.server_sock.bind((HOST, PORT))
        self.server_sock.listen(MAX_PLAYERS)
        log.info(f"{'='*50}")
        log.info(f"  Online Okey Sunucusu Başlatıldı")
        log.info(f"  Adres : {HOST}:{PORT}")
        log.info(f"  Kapasite: {MAX_PLAYERS} oyuncu")
        log.info(f"  Zaman Aşımı: {TURN_TIMEOUT} saniye")
        log.info(f"{'='*50}")
        log.info("Oyuncular bekleniyor...")

        while self._running:
            try:
                client_sock, address = self.server_sock.accept()
                with self.lock:
                    if len(self.clients) >= MAX_PLAYERS:
                        self._send(client_sock, {
                            "type":    MsgType.ERROR,
                            "message": "Oyun dolu. Daha sonra tekrar deneyin."
                        })
                        client_sock.close()
                        log.warning(f"Bağlantı reddedildi (dolu): {address}")
                        continue
                log.info(f"Yeni bağlantı isteği: {address}")
                t = threading.Thread(
                    target=self._handle_client,
                    args=(client_sock,),
                    daemon=True,
                    name=f"Client-{address}"
                )
                t.start()
            except OSError:
                break

     # ─── Oyun Başlatma ───────────────────────────────────────
    def _start_game(self):
        """Oyunu başlatır ve ilk durumu tüm istemcilere gönderir."""
        self.game.start_game()
        self.last_action_time = time.time() # Zamanlayıcıyı başlat

        starter = self.game.get_current_player()
        log.info(f"★ Oyun başladı! İlk sıra: {starter['name']!r}")

        self._broadcast({
            "type":         MsgType.GAME_START,
            "message":      "Oyun başlıyor! İyi oyunlar!",
            "starter_name": starter["name"],
            "starter_id":   starter["id"],
        })
        self._broadcast_state()

        # Timer iş parçacığını sadece bir kere başlat[cite: 4]
        if not self.timer_thread_started:
            self.timer_thread_started = True
            threading.Thread(target=self._turn_timer_monitor, daemon=True).start()

    # ─── Otomatik Oyun Zamanlayıcısı ─────────────────────────
    def _turn_timer_monitor(self):
        """Zamanı dolan oyuncunun yerine otomatik hamle yapar."""
        while self._running:
            time.sleep(1)
            if self.game.phase != "playing":
                continue

            with self.lock:
                # Oyun oynanıyorken kontrol et
                if self.game.phase == "playing":
                    elapsed = time.time() - self.last_action_time
                    if elapsed > TURN_TIMEOUT:
                        current_player = self.game.get_current_player()
                        if not current_player:
                            continue

                        log.info(f"⏰ [Zaman Aşımı] {current_player['name']} için otomatik hamle yapılıyor.")

                        # 1. Eğer oyuncu henüz taş çekmemişse yığından çek
                        if not self.game.has_drawn:
                            self.game.draw_from_pile(current_player["id"])
                            log.info(f"  ↳ Otomatik taş çekildi.")

                        # 2. Şimdi mutlaka elinden bir taş atmalı (Eldeki ilk taşı atıyoruz)
                        if self.game.has_drawn and current_player["hand"]:
                            tile_to_discard = current_player["hand"][0].to_dict()
                            self.game.discard_tile(current_player["id"], tile_to_discard)
                            log.info(f"  ↳ Otomatik taş atıldı.")

                        self.last_action_time = time.time()
                        self._broadcast_state()

    # ─── Mesaj İşleme ────────────────────────────────────────
    def _handle_message(self, player_id: int, msg: dict):
        msg_type = msg.get("type")

        with self.lock:
            if self.game.phase == "waiting":
                return

            if msg_type == MsgType.DRAW:
                ok, result = self.game.draw_from_pile(player_id)
                if ok:
                    log.info(f"[Çek] {self.player_names[player_id]} → {result}")
                    self.last_action_time = time.time() # Zamanlayıcıyı sıfırla
                    self._broadcast_state()
                else:
                    self._send_to(player_id, {"type": MsgType.ERROR, "message": result})

            elif msg_type == MsgType.DRAW_DISCARD:
                ok, result = self.game.draw_from_discard(player_id)
                if ok:
                    log.info(f"[Atık çek] {self.player_names[player_id]} → {result}")
                    self.last_action_time = time.time() # Zamanlayıcıyı sıfırla
                    self._broadcast_state()
                else:
                    self._send_to(player_id, {"type": MsgType.ERROR, "message": result})

            elif msg_type == MsgType.DISCARD:
                tile_dict = msg.get("tile")
                if not tile_dict:
                    return
                ok, result = self.game.discard_tile(player_id, tile_dict)
                if ok:
                    log.info(f"[At] {self.player_names[player_id]} → {result}")
                    self.last_action_time = time.time() # Sonraki oyuncu için zamanlayıcıyı sıfırla
                    self._broadcast_state()
                else:
                    self._send_to(player_id, {"type": MsgType.ERROR, "message": result})

            elif msg_type == MsgType.WIN:
                ok, message = self.game.declare_win(player_id)
                if ok:
                    winner_name = self.player_names.get(player_id, "?")
                    log.info(f"★★★ Kazanan: {winner_name!r} ★★★")
                    self._broadcast({
                        "type":        MsgType.GAME_OVER,
                        "winner_id":   player_id,
                        "winner_name": winner_name,
                        "message":     f"{winner_name} okey yaptı! 🎉"
                    })
                else:
                    self._send_to(player_id, {"type": MsgType.ERROR, "message": message})

            elif msg_type == MsgType.CHAT:
                text = msg.get("message", "").strip()
                if text:
                    name = self.player_names.get(player_id, "?")
                    log.info(f"[Chat] {name}: {text}")
                    self._broadcast({
                        "type":        MsgType.CHAT_BROADCAST,
                        "player_name": name,
                        "player_id":   player_id,
                        "message":     text
                    })

    # ─── Yayın / Gönderme ────────────────────────────────────
    def _broadcast_state(self):
        for pid in list(self.clients.keys()):
            state = self.game.get_state_for_player(pid)
            state["type"] = MsgType.GAME_STATE
            self._send_to(pid, state)

    def _broadcast(self, data: dict):
        for pid in list(self.clients.keys()):
            self._send_to(pid, data)

    def _send_to(self, player_id: int, data: dict):
        if player_id in self.clients:
            self._send(self.clients[player_id], data)

    def _send(self, sock: socket.socket, data: dict):
        try:
            msg = json.dumps(data, ensure_ascii=False) + "\n"
            sock.sendall(msg.encode("utf-8"))
        except Exception as e:
            log.error(f"Gönderme hatası: {e}")

    # ─── İstemci Handler ─────────────────────────────────────
    def _handle_client(self, client_sock: socket.socket):
        player_id = None
        player_name = None
        buffer = ""

        try:
            # 1. HAMACHI FİXİ: İlk mesajı (JOIN) parçalanma ihtimaline karşı güvenle bekle
            msg = None
            while True:
                chunk = client_sock.recv(BUFFER_SIZE).decode("utf-8", errors="ignore")
                if not chunk:
                    break
                buffer += chunk
                if "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    msg = parse(line.strip())
                    break

            if not msg or msg.get("type") != MsgType.JOIN:
                log.warning("Geçersiz giriş mesajı, bağlantı kapatıldı.")
                client_sock.close()
                return

            player_name = msg.get("player_name", "Anonim")[:20].strip() or "Anonim"

            with self.lock:
                player_id = self.next_id
                self.next_id += 1
                self.clients[player_id] = client_sock
                self.player_names[player_id] = player_name
                self.game.add_player(player_id, player_name)

                log.info(f"✔ Oyuncu katıldı: {player_name!r}  (ID={player_id})")

                self._broadcast({
                    "type": MsgType.WAITING,
                    "count": len(self.clients),
                    "max": MAX_PLAYERS,
                    "players": [self.player_names[pid] for pid in self.clients]
                })

                if len(self.clients) == MAX_PLAYERS:
                    self._start_game()

            # Geri kalan mesajları dinleme döngüsü (Değişiklik yok)
            while True:
                chunk = client_sock.recv(BUFFER_SIZE).decode("utf-8", errors="ignore")
                if not chunk:
                    break
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        parsed = parse(line)
                        if parsed:
                            self._handle_message(player_id, parsed)

        except (ConnectionResetError, BrokenPipeError):
            log.info(f"Bağlantı kesildi: {player_name!r}")
        except Exception as e:
            log.error(f"İstemci hatası ({player_name}): {e}", exc_info=True)
        finally:
            if player_id is not None:
                self._remove_player(player_id, player_name)

    # ─── Oyuncu Çıkışı ───────────────────────────────────────
    def _remove_player(self, player_id: int, name: str):
        with self.lock:
            if player_id in self.clients:
                try:
                    self.clients[player_id].close()
                except Exception:
                    pass
                del self.clients[player_id]
                self.player_names.pop(player_id, None)

                # HAYALET OYUNCU FİXİ: Ağdan düşen oyuncuyu oyun mantığından da sil
                if hasattr(self.game, 'remove_player'):
                    self.game.remove_player(player_id)

                log.info(f"✖ Oyuncu ayrıldı: {name!r}")

                if self.game.phase == "playing":
                    self.game.phase = "waiting"  # Oyunculardan biri çıktığı için oyunu duraklat
                    self._broadcast({
                        "type": MsgType.ERROR,
                        "message": f"'{name}' oyundan ayrıldı. Oyun duraklatıldı."
                    })

# ─────────────────────────────────────────────────────────────
#  Giriş Noktası
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    server = OkeyServer()
    try:
        server.start()
    except KeyboardInterrupt:
        log.info("Sunucu kapatılıyor...")
        server._running = False
        server.server_sock.close()
        sys.exit(0)