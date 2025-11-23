from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Set, Callable, Dict, Optional

import config


class Action(Enum):
    # OO rationale: Domain vocabulary for player intents. Using an Enum fixes the set
    # of valid actions at compile-time, enabling explicit branching and avoiding
    # stringly-typed conditionals throughout the system.
    USE_POTION = auto()
    FLEE = auto()
    SWORD_SLASH = auto()
    SHIELD_BASH = auto()
    HOLY_SMITE = auto()


class Weakness(Enum):
    # OO rationale: Encodes monster susceptibility traits. Separating weaknesses
    # from abilities supports simple mapping logic (action -> weakness) and
    # keeps combat rules declarative.
    SWORD_SLASH = auto()
    SHIELD_BASH = auto()
    HOLY_SMITE = auto()


class DropResult(Enum):
    # OO rationale: Single source of truth for all drop types (consumables
    # and player's unique stolen gear). Enables centralized probability
    # tables and uniform handling of loot application without ad-hoc strings.
    NO_ITEM = auto()
    HEALTH_POTION = auto()
    ESCAPE_SCROLL = auto()
    SHIELD = auto()  # guaranteed on 1st monster
    SWORD = auto()   # guaranteed on 3rd monster
    HELM = auto()
    PAULDRONS = auto()
    CUIRASS = auto()
    GAUNTLETS = auto()
    LEG_GUARDS = auto()
    BOOTS = auto()

    @classmethod
    def armor_pieces(cls) -> List["DropResult"]:
        return [
            cls.HELM,
            cls.PAULDRONS,
            cls.CUIRASS,
            cls.GAUNTLETS,
            cls.LEG_GUARDS,
            cls.BOOTS,
        ]


@dataclass
class Actor:
    # OO rationale: Abstract base for battle participants capturing shared
    # invariants (health bounds) and behavior (damage application, aliveness).
    # Subtypes (Player, Monster) specialize without duplicating core combat math.
    max_health: int
    strength: int
    health: int = field(init=False)

    def __post_init__(self) -> None:
        self.health = self.max_health

    def take_damage(self, raw_damage: int, defense: int = 0) -> int:
        """Apply damage reduced by defense; returns actual damage taken."""
        reduced = max(0, raw_damage - max(0, defense))
        self.health = max(0, self.health - reduced)
        return reduced

    def is_alive(self) -> bool:
        return self.health > 0


@dataclass
class Inventory:
    # OO rationale: Encapsulates consumable counts and rules for mutation,
    # enforcing invariants (no negative counts) at a single point. Keeps
    # Player focused on combat and equipment rather than item bookkeeping.
    num_potions: int = 0
    num_escape_scrolls: int = 0

    def add_potion(self, amount: int = 1) -> None:
        self.num_potions += max(0, amount)

    def remove_potion(self, amount: int = 1) -> bool:
        if self.num_potions >= amount:
            self.num_potions -= amount
            return True
        return False

    def add_escape_scroll(self, amount: int = 1) -> None:
        self.num_escape_scrolls += max(0, amount)

    def remove_escape_scroll(self, amount: int = 1) -> bool:
        if self.num_escape_scrolls >= amount:
            self.num_escape_scrolls -= amount
            return True
        return False


@dataclass
class Player(Actor):
    # OO rationale: Concrete combatant with composition (Inventory) and
    # capabilities (abilities map). Keeps responsibility cohesive: defense,
    # healing, fleeing, and equipping armor are player-specific concerns.
    base_defense: int = config.PLAYER_BASE_DEFENSE
    inventory: Inventory = field(default_factory=Inventory)
    owned_armor: Set[DropResult] = field(default_factory=set)
    has_shield: bool = False  # unlocks after first monster fight
    has_sword: bool = False   # unlocks after third monster fight

    def get_defense(self) -> int:
        return self.base_defense + len(self.owned_armor) * config.ARMOR_DEFENSE_BONUS_PER_PIECE

    def add_armor_piece(self, armor_piece: DropResult) -> None:
        if armor_piece in DropResult.armor_pieces() and armor_piece not in self.owned_armor:
            self.owned_armor.add(armor_piece)

    def use_potion(self) -> bool:
        if self.inventory.remove_potion():
            self.health = self.max_health
            return True
        return False

    def attempt_flee(self, random_func: Callable[[], float] | None = None) -> bool:
        # Escape scroll guarantees flee
        if self.inventory.remove_escape_scroll():
            return True
        # Otherwise chance-based
        roll = (random_func or random.random)()
        return roll < config.FLEE_SUCCESS_CHANCE

    def holy_smite(self) -> int:
        base = config.HOLY_SMITE_BASE_DAMAGE + self.strength
        return base

    def sword_slash(self) -> int:
        base = config.SWORD_SLASH_BASE_DAMAGE + self.strength
        return base

    def shield_bash(self) -> int:
        base = config.SHIELD_BASH_BASE_DAMAGE + self.strength
        return base

    def pray_for_restoration(self) -> None:
        self.health = self.max_health

    def abilities(self) -> Dict[Action, Callable[[], int]]:
        mapping: Dict[Action, Callable[[], int]] = {Action.HOLY_SMITE: self.holy_smite}
        if self.has_sword:
            mapping[Action.SWORD_SLASH] = self.sword_slash
        if self.has_shield:
            mapping[Action.SHIELD_BASH] = self.shield_bash
        return mapping


@dataclass
class Monster(Actor):
    # OO rationale: Concrete combatant representing adversaries. Holds static
    # traits (name, description) and combat modifiers (weaknesses).
    # Weakness handling is encapsulated to keep GameSystem orchestration lean.
    name: str = "Unknown"
    weaknesses: List[Weakness] = field(default_factory=list)
    description: str = ""
    is_boss: bool = False
    item_drop: Optional["DropResult"] = None

    def attack(self) -> int:
        # Slight randomness to monster damage
        variance = random.randint(0, 2)
        return self.strength + variance

    def apply_weakness_bonus(self, action: Action, base_damage: int) -> int:
        action_to_weakness = {
            Action.HOLY_SMITE: Weakness.HOLY_SMITE,
            Action.SWORD_SLASH: Weakness.SWORD_SLASH,
            Action.SHIELD_BASH: Weakness.SHIELD_BASH,
        }
        weakness_for_action = action_to_weakness.get(action)
        if weakness_for_action is not None and weakness_for_action in self.weaknesses:
            return base_damage + config.WEAKNESS_BONUS_DAMAGE
        return base_damage
