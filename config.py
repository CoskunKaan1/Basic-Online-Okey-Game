# ============================================================
#  ONLINE OKEY OYUNU — config.py
#  Tüm sabit ayarlar bu dosyada tanımlanır.
# ============================================================

# ── Ağ Ayarları ──────────────────────────────────────────────
HOST        = "127.0.0.1"   # Sunucu IP (LAN için değiştirin)
PORT        = 5555           # Bağlantı portu
MAX_PLAYERS = 4           # Oyun başlamak için gereken oyuncu sayısı
BUFFER_SIZE = 8192           # TCP tampon boyutu (byte)

# ── Oyun Kuralları ───────────────────────────────────────────
TILES_PER_PLAYER        = 14  # Her oyuncuya dağıtılan taş
STARTING_PLAYER_EXTRA   = 1   # Başlayan oyuncunun fazladan taşı
TOTAL_TILES             = 106 # 4×13×2 + 2 sahte joker

# ── Renkler (Okey taşı renkleri) ─────────────────────────────
TILE_COLORS = ["kirmizi", "sari", "mavi", "siyah"]

# ── Zaman Aşımı (saniye) ─────────────────────────────────────
TURN_TIMEOUT        = 60   # Sıra başına maksimum süre
CONNECTION_TIMEOUT  = 10   # Bağlantı zaman aşımı

# ── Arayüz ───────────────────────────────────────────────────
WINDOW_TITLE    = "Online Okey"
WINDOW_WIDTH    = 1280
WINDOW_HEIGHT   = 800
MIN_WIDTH       = 1100
MIN_HEIGHT      = 700
TILE_WIDTH  = 56
TILE_HEIGHT = 80
RACK_ROWS   = 2
RACK_COLS   = 11