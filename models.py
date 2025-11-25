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


class RoomType(Enum):
    # OO rationale: Enum for different room types in the dungeon, providing
    # type safety and preventing magic string errors in room generation.
    EMPTY = "empty"
    LOOT = "loot"
    MONSTER = "monster"


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
    def unique_gear(cls) -> List["DropResult"]:
        """Return all unique gear items (shield, sword, and armor pieces)."""
        return [
            cls.SHIELD,
            cls.SWORD,
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

    def take_damage(self, incoming_damage: int, defense: int = 0) -> int:
        """Apply damage reduced by defense; returns actual damage taken."""
        damage_after_defense = max(0, incoming_damage - max(0, defense))
        self.health = max(0, self.health - damage_after_defense)
        return damage_after_defense

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
        defense_from_armor = len(self.owned_armor) * config.ARMOR_DEFENSE_BONUS_PER_PIECE
        defense_from_shield = 3 if self.has_shield else 0
        return self.base_defense + defense_from_armor + defense_from_shield

    def add_armor_piece(self, armor_piece: DropResult) -> None:
        """Add an armor piece to the player's owned armor set."""
        if armor_piece not in self.owned_armor:
            self.owned_armor.add(armor_piece)

    def use_potion(self) -> bool:
        if self.inventory.remove_potion():
            self.health = self.max_health
            return True
        return False

    def attempt_flee(self, random_generator: Callable[[], float] | None = None) -> bool:
        # Escape scroll guarantees flee
        if self.inventory.remove_escape_scroll():
            return True
        # Otherwise chance-based
        flee_roll = (random_generator or random.random)()
        return flee_roll < config.FLEE_SUCCESS_CHANCE

    def holy_smite(self) -> int:
        base_damage = config.HOLY_SMITE_BASE_DAMAGE + self.strength
        return base_damage

    def sword_slash(self) -> int:
        base_damage = config.SWORD_SLASH_BASE_DAMAGE + self.strength
        return base_damage

    def shield_bash(self) -> int:
        base_damage = config.SHIELD_BASH_BASE_DAMAGE + self.strength
        return base_damage

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
        damage_variance = random.randint(0, 2)
        return self.strength + damage_variance

    def apply_weakness_bonus(self, action: Action, base_damage: int) -> int:
        ACTION_WEAKNESS_MAP = {
            Action.HOLY_SMITE: Weakness.HOLY_SMITE,
            Action.SWORD_SLASH: Weakness.SWORD_SLASH,
            Action.SHIELD_BASH: Weakness.SHIELD_BASH,
        }
        matching_weakness = ACTION_WEAKNESS_MAP.get(action)
        if matching_weakness is not None and matching_weakness in self.weaknesses:
            return base_damage + config.WEAKNESS_BONUS_DAMAGE
        return base_damage


@dataclass
class ActionOption:
    """Represents a menu option with its display label and action identifier.

    OO rationale: Encapsulates UI choice data, separating display concerns
    from action logic. Enables clean menu generation and selection handling.

    Attributes:
        display_label: The text shown to the user in the menu
        action_id: The identifier used by the code to determine what action to perform
    """
    display_label: str
    action_id: str


@dataclass
class MonsterTemplate:
    """Template for generating monsters with consistent attributes.

    OO rationale: Data model for monster generation, encapsulating all
    monster attributes in a type-safe structure. Supports both random
    and fixed attribute generation through optional fields.
    """
    name: str
    weaknesses: List[Weakness]
    description: str
    hp: Optional[int] = None  # If None, use random range
    strength: Optional[int] = None  # If None, use random range
    is_boss: bool = False


@dataclass
class RoomTypeOption:
    """Represents a room type with its spawn probability.

    OO rationale: Data model for room configuration, encapsulating
    room type and weight in a validated structure for room generation.
    """
    room_type: RoomType
    spawn_weight: float

    def __post_init__(self) -> None:
        if self.spawn_weight < 0:
            raise ValueError(f"Spawn weight must be non-negative, got {self.spawn_weight}")

@dataclass
class WeightedOption:
    """A weighted option for random selection with validation."""
    label: str
    weight: float

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise ValueError(f"Weight must be non-negative, got {self.weight}")
