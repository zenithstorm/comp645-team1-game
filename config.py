# Tuning constants for the simple dungeon crawler
from __future__ import annotations

# Player and combat values
PLAYER_MAX_HEALTH: int = 20
PLAYER_BASE_STRENGTH: int = 5
PLAYER_BASE_DEFENSE: int = 1

# Monster ranges
MONSTER_HEALTH_MIN: int = 16
MONSTER_HEALTH_MAX: int = 26
MONSTER_STRENGTH_MIN: int = 3
MONSTER_STRENGTH_MAX: int = 7

# Abilities base damage
HOLY_SMITE_BASE_DAMAGE: int = 6
SWORD_SLASH_BASE_DAMAGE: int = 8
SHIELD_BASH_BASE_DAMAGE: int = 5

# Weakness bonus damage
WEAKNESS_BONUS_DAMAGE: int = 5

# Armor defense
ARMOR_DEFENSE_BONUS_PER_PIECE: int = 2

# Fleeing
FLEE_SUCCESS_CHANCE: float = 0.5  # used when no escape scroll

# Boss tuning
BOSS_HP: int = 45
BOSS_STRENGTH: int = 9
BOSS_SPAWN_THRESHOLD: int = 3  # minimum defeated monsters before boss can appear
BOSS_SPAWN_CHANCE: float = 0.2  # chance per monster room after threshold

# Room selection weights (must sum to ~1.0)
ROOM_TYPE_WEIGHTS = {
    "empty": 0.1,
    "loot": 0.1,
    "monster": 0.8,
}

# Loot probabilities (used by DropCalculator)
DROP_WEIGHTS = {
    "NO_ITEM": 0.4,
    "HEALTH_POTION": 0.25,
    "ESCAPE_SCROLL": 0.05,
    "ARMOR": 0.3, # If there are no more armor drops, this weight is added to NO_ITEM
}
