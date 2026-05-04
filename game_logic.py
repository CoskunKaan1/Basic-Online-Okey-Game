# ============================================================
#  ONLINE OKEY OYUNU — game_logic.py
#  Taş oluşturma, dağıtma, sıra yönetimi ve kazanma kontrolü.
# ============================================================

import random
from config import TILE_COLORS, TILES_PER_PLAYER, STARTING_PLAYER_EXTRA

class Tile:
    def __init__(self, color: str, number: int, is_fake_joker: bool = False):
        self.color        = color         
        self.number       = number        
        self.is_fake_joker = is_fake_joker

    def to_dict(self) -> dict:
        return {"color": self.color, "number": self.number, "is_fake_joker": self.is_fake_joker}

    @staticmethod
    def from_dict(d: dict) -> "Tile":
        return Tile(color=d.get("color", "siyah"), number=d.get("number", 0), is_fake_joker=d.get("is_fake_joker", False))

    def __eq__(self, other):
        if not isinstance(other, Tile): return False
        return (self.color == other.color and self.number == other.number and self.is_fake_joker == other.is_fake_joker)

    def __repr__(self):
        return "JOKER" if self.is_fake_joker else f"{self.color}_{self.number}"

    def __hash__(self):
        return hash((self.color, self.number, self.is_fake_joker))


def create_tile_set() -> list[Tile]:
    tiles = []
    for _ in range(2):
        for color in TILE_COLORS:
            for number in range(1, 14):
                tiles.append(Tile(color, number))
    tiles.append(Tile("joker", 0, is_fake_joker=True))
    tiles.append(Tile("joker", 0, is_fake_joker=True))
    return tiles


class GameManager:
    def __init__(self):
        self.players: list[dict]  = []   
        self.draw_pile:    list[Tile] = []
        self.discard_piles: dict[int, list[Tile]] = {} # YENİ: Her oyuncunun sağına attığı kendi yığını
        self.current_turn_index: int  = 0
        self.indicator_tile: Tile | None = None
        self.okey_tile:      Tile | None = None
        self.phase:  str = "waiting"    
        self.winner: int | None = None  
        self.has_drawn: bool = False    

    def add_player(self, player_id: int, player_name: str):
        self.players.append({"id": player_id, "name": player_name, "hand": []})

    def remove_player(self, player_id: int):
        """Oyundan kopan oyuncuyu hafızadan tamamen temizler."""
        self.players = [p for p in self.players if p["id"] != player_id]
        if player_id in self.discard_piles:
            del self.discard_piles[player_id]

    def get_player(self, player_id: int) -> dict | None:
        for p in self.players:
            if p["id"] == player_id: return p
        return None

    def get_current_player(self) -> dict | None:
        return self.players[self.current_turn_index] if self.players else None

    def start_game(self):
        tiles = create_tile_set()
        random.shuffle(tiles)

        self.indicator_tile = tiles.pop()
        self.okey_tile = self._compute_okey(self.indicator_tile)

        for i, player in enumerate(self.players):
            count = TILES_PER_PLAYER + (STARTING_PLAYER_EXTRA if i == 0 else 0)
            player["hand"] = tiles[:count]
            tiles = tiles[count:]

        self.draw_pile = tiles
        self.discard_piles = {p["id"]: [] for p in self.players} # Yığınları sıfırla
        self.current_turn_index = 0
        self.has_drawn = True   
        self.phase = "playing"
        self.winner = None

    def _compute_okey(self, indicator: Tile) -> Tile:
        if indicator.is_fake_joker: return Tile("kirmizi", 1)
        next_num = (indicator.number % 13) + 1
        return Tile(indicator.color, next_num)

    def draw_from_pile(self, player_id: int) -> tuple[bool, object]:
        player = self.get_player(player_id)
        if not player or player["id"] != self.get_current_player()["id"]: return False, "Sıra sizde değil."
        if self.has_drawn: return False, "Zaten taş çektiniz."
        if not self.draw_pile: return False, "Yığında taş kalmadı."

        tile = self.draw_pile.pop(0)
        player["hand"].append(tile)
        self.has_drawn = True
        return True, tile

    def draw_from_discard(self, player_id: int) -> tuple[bool, object]:
        """Solundaki oyuncunun (önceki sıradaki) attığı taşı çek."""
        player = self.get_player(player_id)
        if not player or player["id"] != self.get_current_player()["id"]: return False, "Sıra sizde değil."
        if self.has_drawn: return False, "Zaten taş çektiniz."
        
        # Sol oyuncuyu bul (indeks olarak bir önceki)
        prev_idx = (self.current_turn_index - 1) % len(self.players)
        prev_player_id = self.players[prev_idx]["id"]
        
        if not self.discard_piles.get(prev_player_id): return False, "Solunuzda çekilecek taş yok."

        tile = self.discard_piles[prev_player_id].pop()
        player["hand"].append(tile)
        self.has_drawn = True
        return True, tile

    def discard_tile(self, player_id: int, tile_dict: dict) -> tuple[bool, object]:
        """Eldeki bir taşı kendi sağına at."""
        player = self.get_player(player_id)
        if not player or player["id"] != self.get_current_player()["id"]: return False, "Sıra sizde değil."
        if not self.has_drawn: return False, "Önce taş çekmelisiniz."

        tile_to_drop = self._find_tile_in_hand(player["hand"], tile_dict)
        if not tile_to_drop: return False, "Bu taş elinizde bulunamadı."

        player["hand"].remove(tile_to_drop)
        self.discard_piles[player_id].append(tile_to_drop) # Sağıma attım

        self.current_turn_index = (self.current_turn_index + 1) % len(self.players)
        self.has_drawn = False
        return True, tile_to_drop

    def declare_win(self, player_id: int) -> tuple[bool, str]:
        player = self.get_player(player_id)
        if not player or player["id"] != self.get_current_player()["id"]: return False, "Sıra sizde değil."
        if not self.has_drawn: return False, "Önce taş çekmelisiniz."

        if self._validate_hand(player["hand"]):
            self.phase = "finished"
            self.winner = player_id
            return True, "Tebrikler! Okey!"
        return False, "Geçersiz el! Devam edin."

    def _validate_hand(self, hand: list[Tile]) -> bool:
        if len(hand) != TILES_PER_PLAYER: return False
        return self._can_partition(hand[:])

    def _can_partition(self, tiles: list[Tile]) -> bool:
        jokers = sum(1 for t in tiles if t.is_fake_joker or t == self.okey_tile)
        normals = [t for t in tiles if not t.is_fake_joker and t != self.okey_tile]

        if not normals: return True
        normals.sort(key=lambda t: (t.color, t.number))
        first, rest = normals[0], normals[1:]

        same_num = [t for t in rest if t.number == first.number and t.color != first.color]
        for size in range(min(3, len(same_num) + 1), 0, -1):
            group = [first] + same_num[:size - 1]
            need = max(0, 3 - len(group))
            if need <= jokers and len(group) + need >= 3:
                if self._can_partition_with_jokers([t for t in rest if t not in group], jokers - need): return True

        same_col = sorted([t for t in rest if t.color == first.color], key=lambda t: t.number)
        chain = [first]
        for t in same_col:
            if t.number == chain[-1].number + 1: chain.append(t)
        for size in range(min(len(chain), 13), 2, -1):
            if len(chain[:size]) >= 3:
                if self._can_partition_with_jokers([t for t in rest if t not in chain[:size]], jokers): return True

        return False

    def _can_partition_with_jokers(self, tiles: list[Tile], jokers: int) -> bool:
        if not tiles: return True
        return self._can_partition(tiles + [Tile("joker", 0, True)] * jokers) if jokers else self._can_partition(tiles)

    def _find_tile_in_hand(self, hand: list[Tile], tile_dict: dict) -> Tile | None:
        for t in hand:
            if (t.color == tile_dict.get("color") and t.number == tile_dict.get("number") and t.is_fake_joker == tile_dict.get("is_fake_joker", False)):
                return t
        return None

    def get_state_for_player(self, player_id: int) -> dict:
        current = self.get_current_player()
        
        my_idx = next((i for i, p in enumerate(self.players) if p["id"] == player_id), 0)
        prev_idx = (my_idx - 1) % len(self.players)
        prev_player_id = self.players[prev_idx]["id"] if self.players else -1

        left_pile = self.discard_piles.get(prev_player_id, [])
        my_pile = self.discard_piles.get(player_id, [])

        state = {
            "phase":               self.phase,
            "current_turn_id":     current["id"] if current else None,
            "draw_pile_count":     len(self.draw_pile),
            "has_drawn":           self.has_drawn,
            "left_discard_top":    left_pile[-1].to_dict() if left_pile else None,
            "my_discard_top":      my_pile[-1].to_dict() if my_pile else None,
            "indicator_tile":      self.indicator_tile.to_dict() if self.indicator_tile else None,
            "okey_tile":           self.okey_tile.to_dict() if self.okey_tile else None,
            "winner_id":           self.winner,
            "players":             [],
            "my_hand":             [],
            "my_id":               player_id,
        }

        for p in self.players:
            state["players"].append({"id": p["id"], "name": p["name"], "tile_count": len(p["hand"])})
            if p["id"] == player_id:
                state["my_hand"] = [t.to_dict() for t in p["hand"]]

        return state