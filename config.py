# Tuning constants for the simple dungeon crawler
from __future__ import annotations

# Player and combat values
PLAYER_MAX_HEALTH: int = 30
PLAYER_BASE_STRENGTH: int = 5
PLAYER_BASE_DEFENSE: int = 1

# Monster ranges
MONSTER_HEALTH_MIN: int = 12
MONSTER_HEALTH_MAX: int = 22
MONSTER_STRENGTH_MIN: int = 2
MONSTER_STRENGTH_MAX: int = 6

# Abilities base damage
HOLY_SMITE_BASE_DAMAGE: int = 7
SWORD_SLASH_BASE_DAMAGE: int = 9
SHIELD_BASH_BASE_DAMAGE: int = 6

# Weakness bonus damage
WEAKNESS_BONUS_DAMAGE: int = 5

# Armor defense
ARMOR_DEFENSE_BONUS_PER_PIECE: int = 2

# Fleeing
FLEE_SUCCESS_CHANCE: float = 0.5  # used when no escape scroll

# Boss tuning
BOSS_HP: int = 45
BOSS_STRENGTH: int = 9
BOSS_SPAWN_THRESHOLD: int = 4  # minimum defeated monsters before boss can appear
BOSS_SPAWN_CHANCE: float = 0.2  # chance per monster room after threshold

# Room selection weights (must sum to ~1.0)
ROOM_TYPE_WEIGHTS = {
    "empty": 0.4,
    "loot": 0.2,
    "monster": 0.4,
}

# Loot probabilities (used by DropCalculator)
DROP_WEIGHTS = {
    "NO_ITEM": 0.4,
    "HEALTH_POTION": 0.3,
    "ESCAPE_SCROLL": 0.2,
    # Armor has a small chance; if exhausted, it falls back to other results
    "ARMOR": 0.1,
}
