# ============================================================
#  ONLINE OKEY OYUNU — protocol.py
#  JSON mesaj tipleri ve yardımcı fonksiyonlar.
# ============================================================

import json


# ── Mesaj Tipleri ────────────────────────────────────────────
class MsgType:
    # İstemci → Sunucu
    JOIN          = "join"          # Oyuna katılma
    DRAW          = "draw"          # Dağıtma yığınından taş çek
    DRAW_DISCARD  = "draw_discard"  # Atık yığınından taş çek
    DISCARD       = "discard"       # Taş at
    WIN           = "win"           # Okey ilan et
    CHAT          = "chat"          # Sohbet mesajı

    # Sunucu → İstemci
    WAITING         = "waiting"         # Oyuncu bekleme odası
    GAME_START      = "game_start"      # Oyun başladı
    GAME_STATE      = "game_state"      # Oyun durumu güncellendi
    GAME_OVER       = "game_over"       # Oyun bitti
    ERROR           = "error"           # Hata mesajı
    CHAT_BROADCAST  = "chat_broadcast"  # Sohbet yayını


# ── İstemci → Sunucu Mesaj Oluşturucular ─────────────────────

def build_join(player_name: str) -> str:
    """Oyuna katılma mesajı."""
    return json.dumps({
        "type": MsgType.JOIN,
        "player_name": player_name.strip()
    }, ensure_ascii=False)


def build_draw() -> str:
    """Dağıtma yığınından taş çekme mesajı."""
    return json.dumps({"type": MsgType.DRAW})


def build_draw_discard() -> str:
    """Atık yığınının üstündeki taşı çekme mesajı."""
    return json.dumps({"type": MsgType.DRAW_DISCARD})


def build_discard(tile_dict: dict) -> str:
    """Seçili taşı atma mesajı."""
    return json.dumps({
        "type": MsgType.DISCARD,
        "tile": tile_dict
    }, ensure_ascii=False)


def build_win() -> str:
    """Okey ilan etme mesajı."""
    return json.dumps({"type": MsgType.WIN})


def build_chat(message: str) -> str:
    """Sohbet mesajı."""
    return json.dumps({
        "type": MsgType.CHAT,
        "message": message.strip()
    }, ensure_ascii=False)


# ── Yardımcı ─────────────────────────────────────────────────

def parse(raw: str) -> dict | None:
    """JSON string'i dict'e dönüştürür. Hata varsa None döner."""
    try:
        return json.loads(raw.strip())
    except (json.JSONDecodeError, AttributeError):
        return None


def tile_to_label(tile_dict: dict) -> str:
    """Taşı okunabilir metne çevirir. Örn: 'Kırmızı 7'"""
    if tile_dict is None:
        return "?"
    if tile_dict.get("is_fake_joker"):
        return "Sahte Joker"
    color_names = {
        "kirmizi": "Kırmızı",
        "sari":    "Sarı",
        "mavi":    "Mavi",
        "siyah":   "Siyah",
    }
    color = color_names.get(tile_dict.get("color", ""), tile_dict.get("color", ""))
    number = tile_dict.get("number", "?")
    return f"{color} {number}"
