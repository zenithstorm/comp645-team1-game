from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Protocol, Any, Callable

import config
import ui
from models import (
    Action,
    ActionOption,
    DropResult,
    Monster,
    MonsterTemplate,
    Player,
    RoomType,
    RoomTypeOption,
    Weakness,
)


class StoryTellerProtocol(Protocol):
    # OO rationale: Behavioral contract for narrative providers. Allows the
    # game loop to depend on an interface instead of a concrete type.
    def track_event(self, event_type: str, description: str) -> None: ...

class RandomProvider(Protocol):
    # OO rationale: Small RNG abstraction to make probabilistic systems
    # deterministic in tests and swappable in production.
    def random(self) -> float: ...
    def randint(self, a: int, b: int) -> int: ...
    def choice(self, seq: List[Any]) -> Any: ...

class DefaultRandomProvider:
    # OO rationale: Default implementation bridging to Python's random module.
    def random(self) -> float:
        return random.random()
    def randint(self, a: int, b: int) -> int:
        return random.randint(a, b)
    def choice(self, seq: List[Any]) -> Any:
        return random.choice(seq)

def select_weighted_random(options: List[WeightedOption], random_provider: RandomProvider) -> str:
    """Select a random option from weighted choices using probability distribution.

    This function implements weighted random selection, where each option has a
    probability of being selected proportional to its weight. Higher weights
    mean higher probability of selection.

    Algorithm:
    1. Calculate total weight of all options
    2. Generate a random number between 0 and total_weight
    3. Iterate through options, accumulating weights until the random number
       falls within an option's range
    4. Return the label of the selected option

    Example:
        options = [
            WeightedOption("common", 10.0),   # 10/15 = 66.7% chance
            WeightedOption("rare", 4.0),      # 4/15 = 26.7% chance
            WeightedOption("epic", 1.0)       # 1/15 = 6.7% chance
        ]
        # Total weight = 15.0
        # Random number between 0-15 determines which option is selected

    Args:
        options: List of WeightedOption instances. Weight must be >= 0.
        random_provider: Random number generator (for testability).

    Returns:
        The label string of the selected option. If total_weight <= 0, returns
        the last option's label as a fallback.

    OO rationale: Centralized, pure utility that implements weighted selection.
    - Single-responsibility: callers (loot, rooms) don't duplicate probability logic.
    - Dependency inversion: consumes RandomProvider to remain deterministic in tests.
    - Decoupling: returns a label, letting each subsystem map labels to domain types.
    """
    if not options:
        raise ValueError("Cannot select from empty options list")

    total_weight = sum(option.weight for option in options)
    if total_weight <= 0:
        # Fallback: if all weights are zero/negative, return the last option as default
        default_option = options[-1]
        return default_option.label

    # Generate random number in range [0, total_weight)
    random_value = random_provider.random() * total_weight

    # Walk through options, accumulating weights until random_value falls within an option's range
    cumulative_weight = 0.0
    for option in options:
        cumulative_weight += option.weight
        if random_value <= cumulative_weight:
            return option.label

    # Fallback (shouldn't normally reach here due to floating point precision)
    # If we somehow didn't select anything, return the last option as default
    fallback_option = options[-1]
    return fallback_option.label

class MonsterGenerator:
    # OO rationale: Factory responsible for building fully-formed Monster
    # instances from templates. Centralizes variability (names, stats,
    # weaknesses) and keeps creation logic out of the game loop.
    """Generates a single monster from a simple in-memory table."""

    def __init__(self, random_provider: RandomProvider) -> None:
        self.random_provider = random_provider
        self._templates = [
            # Regular foes
            MonsterTemplate(
                name="Skeleton",
                weaknesses=[Weakness.HOLY_SMITE, Weakness.SHIELD_BASH],
                description="A humanoid frame of loose bones held by brittle bindings; light, rattling steps and hollow gaze.",
            ),
            MonsterTemplate(
                name="Goblin Bandit",
                weaknesses=[Weakness.SWORD_SLASH, Weakness.SHIELD_BASH],
                description="A small, agile greenskin with oversized ears and quick hands; favors scavenged gear and sudden lunges.",
            ),
            MonsterTemplate(
                name="Giant Rat",
                weaknesses=[Weakness.SWORD_SLASH],
                description="An oversized rat with patchy fur and prominent incisors; jittery, low to the ground, always testing distance.",
            ),
            MonsterTemplate(
                name="Wraith",
                weaknesses=[Weakness.HOLY_SMITE],
                description="A dim, humanoid outline woven from chill mist; light fades and warmth thins in its presence.",
            ),
        ]

    def generate_monster(self) -> Monster:
        monster_template = self.random_provider.choice(self._templates)
        max_health_points = monster_template.hp or self.random_provider.randint(
            config.MONSTER_HEALTH_MIN, config.MONSTER_HEALTH_MAX
        )
        attack_strength = monster_template.strength or self.random_provider.randint(
            config.MONSTER_STRENGTH_MIN, config.MONSTER_STRENGTH_MAX
        )
        return Monster(
            max_health=max_health_points,
            strength=attack_strength,
            name=monster_template.name,
            weaknesses=list(monster_template.weaknesses),
            description=monster_template.description,
            is_boss=monster_template.is_boss,
        )

    def generate_boss(self) -> Monster:
        # Single end-of-run boss
        boss_template = MonsterTemplate(
            name="Grave Tyrant",
            weaknesses=[],
            description=(
                "An armored lich-king draped in funereal banners. A corroded crown sits on a skull carved with runes; "
                "a great blade of black iron rests across its lap. Plates of ornate mail are missing in places, "
                "revealing ribs choked with grave dust. Clutched in its skeletal grasp, the Heart of Radiance pulses "
                "with a faint, struggling light—the sacred relic you came to reclaim, its divine radiance dimmed but "
                "not extinguished by the creature's dark presence."
            ),
            hp=config.BOSS_HP,
            strength=config.BOSS_STRENGTH,
            is_boss=True,
        )
        # Use the template values directly (no randomization for boss)
        return Monster(
            max_health=boss_template.hp,
            strength=boss_template.strength,
            name=boss_template.name,
            weaknesses=list(boss_template.weaknesses),
            description=boss_template.description,
            is_boss=boss_template.is_boss,
        )

class DropCalculator:
    # OO rationale: Encapsulates loot rules and unique item availability.
    # This isolates drop probability and uniqueness constraints from combat
    # flow, making it easy to tune or swap strategies.
    """Handles loot generation with unique armor pieces and scripted gear recovery."""

    def __init__(self, random_provider: RandomProvider) -> None:
        self.random_provider = random_provider
        # Track all unique gear that can still drop (shield, sword, and armor pieces)
        self._remaining_gear: List[DropResult] = list(DropResult.unique_gear())

    def get_drop_for_monster(self, defeated_count: int, player: Player) -> DropResult:
        """Get the drop for a monster encounter (guaranteed progression items or random drop).

        Checks for guaranteed progression items (shield/sword) first, then falls back
        to a random drop if no guaranteed item is due.

        Args:
            defeated_count: Number of monsters defeated so far
            player: Player instance to check current equipment

        Returns:
            DropResult for the item that will drop
        """
        # Check for guaranteed progression items first
        # Shield guaranteed on 1st monster (defeated_count will be 1 after this fight)
        if defeated_count == 0 and not player.has_shield and DropResult.SHIELD in self._remaining_gear:
            self._remaining_gear.remove(DropResult.SHIELD)
            return DropResult.SHIELD
        # Sword guaranteed on 3rd monster (defeated_count will be 3 after this fight)
        if defeated_count == 2 and not player.has_sword and DropResult.SWORD in self._remaining_gear:
            self._remaining_gear.remove(DropResult.SWORD)
            return DropResult.SWORD
        # Otherwise, roll for a random drop (but exclude shield/sword if already dropped)
        return self.roll_item_drop(player)

    def roll_item_drop(self, player: Player) -> DropResult:
        """Roll for a random item drop, excluding unique items that have already been dropped.

        Args:
            player: Player instance to check current equipment (for defensive checks)
        """

        # Check if any gear (armor pieces) remain
        # Filter _remaining_gear to get only armor pieces (exclude shield and sword)
        remaining_armor = [item for item in self._remaining_gear if item not in (DropResult.SHIELD, DropResult.SWORD)]

        # Create loot buckets using the factory method
        loot_buckets = LootBucket.create_buckets(player, remaining_armor)

        # Convert to WeightedOption for selection
        weighted_options = [WeightedOption(bucket.category, bucket.weight) for bucket in loot_buckets]
        chosen_bucket = select_weighted_random(weighted_options, self.random_provider)

        # Map bucket names to DropResult values
        bucket_to_drop = {
            "NO_ITEM": DropResult.NO_ITEM,
            "HEALTH_POTION": DropResult.HEALTH_POTION,
            "ESCAPE_SCROLL": DropResult.ESCAPE_SCROLL,
        }

        if chosen_bucket in bucket_to_drop:
            return bucket_to_drop[chosen_bucket]

        if chosen_bucket == "ARMOR" and remaining_armor:
            armor_piece = self.random_provider.choice(remaining_armor)
            self._remaining_gear.remove(armor_piece)
            return armor_piece
        return DropResult.NO_ITEM

@dataclass
class WeightedOption:
    """A weighted option for random selection with validation."""
    label: str
    weight: float

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise ValueError(f"Weight must be non-negative, got {self.weight}")


@dataclass
class LootBucket:
    """Represents a loot category with its drop probability."""
    category: str  # Will map to DropResult enum values
    weight: float

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise ValueError(f"Weight must be non-negative, got {self.weight}")

    @classmethod
    def create_buckets(cls, player: 'Player', remaining_armor: List['DropResult']) -> List['LootBucket']:
        """Factory method to create all loot buckets with proper weights."""
        from models import DropResult

        # Build base weights from config
        weight_no_item = config.DROP_WEIGHTS["NO_ITEM"]
        weight_health_potion = config.DROP_WEIGHTS["HEALTH_POTION"]
        weight_escape_scroll = config.DROP_WEIGHTS["ESCAPE_SCROLL"]
        weight_armor = config.DROP_WEIGHTS["ARMOR"] if remaining_armor else 0.0

        # If no armor remains, redistribute armor weight to 'no item'
        if not remaining_armor:
            weight_no_item += config.DROP_WEIGHTS["ARMOR"]

        return [
            cls("NO_ITEM", weight_no_item),
            cls("HEALTH_POTION", weight_health_potion),
            cls("ESCAPE_SCROLL", weight_escape_scroll),
            cls("ARMOR", weight_armor),
        ]


class GameSystem:
    # OO rationale: Orchestrator and state machine for the game flow. It
    # coordinates services (storyteller, RNG, generators) and owns session
    # state (player, current monster). Keeps domain logic cohesive while
    # delegating specialized behavior to collaborators.
    """Main orchestrator for exploration and combat."""

    # Action to weakness mapping (used for combat calculations)
    ACTION_TO_WEAKNESS = {
        Action.HOLY_SMITE: Weakness.HOLY_SMITE,
        Action.SWORD_SLASH: Weakness.SWORD_SLASH,
        Action.SHIELD_BASH: Weakness.SHIELD_BASH,
    }

    def __init__(self, storyteller: StoryTellerProtocol) -> None:
        """Initialize GameSystem with a StoryTeller (required).

        Args:
            storyteller: StoryTeller implementation (typically LLMStoryTeller)
        """
        self.storyteller: StoryTellerProtocol = storyteller
        self.random_provider: RandomProvider = DefaultRandomProvider()
        self.player = Player(
            max_health=config.PLAYER_MAX_HEALTH,
            strength=config.PLAYER_BASE_STRENGTH,
            base_defense=config.PLAYER_BASE_DEFENSE,
        )
        # Player starts injured from the ambush
        self.player.health = 3
        self.current_monster: Optional[Monster] = None
        self.drop_calculator = DropCalculator(self.random_provider)
        self.monster_generator = MonsterGenerator(self.random_provider)
        self.monsters_defeated: int = 0
        self.game_won: bool = False

    def _generate_narrative(
        self,
        narrative_generator: Callable[[], str],
        event_type: Optional[str],
        mode: str = "exploration"
    ) -> None:
        """Generate narrative text with loading indicator and error handling.

        Args:
            narrative_generator: A callable that returns the narrative description string
            event_type: Type of event to track (e.g., "encounter", "victory", "loot") or None to skip tracking
            mode: UI mode for header display ("exploration" or "combat")
        """
        # Clear terminal before showing new narrative
        ui.clear_terminal()

        print("Story Teller is thinking...", end="", flush=True)
        try:
            narrative_text = narrative_generator()
            print("\r" + " " * 30 + "\r", end="", flush=True)
            if event_type:
                self.storyteller.track_event(event_type, narrative_text)
            # Display narrative in a Rich panel
            ui.display_narrative_panel(narrative_text, mode)
        except Exception as e:
            print()
            print(f"Error generating description: {e}", flush=True)
            print("The game cannot continue without the Story Teller. Exiting...", flush=True)
            import sys
            sys.exit(1)

    def _format_item_name(self, item: DropResult) -> Optional[str]:
        """Format a DropResult item name for narrative display.

        Args:
            item: The DropResult item (or None/NO_ITEM for no item)

        Returns:
            Formatted item name (e.g., "a shield", "health potion") or None if no item
        """
        if item is None or item == DropResult.NO_ITEM:
            return None
        if item == DropResult.SHIELD:
            return "a shield"
        if item == DropResult.SWORD:
            return "a sword"
        return item.name.replace("_", " ").lower()

    def start_game(self) -> None:
        opening_text = """You awaken on the cold stone floor of a ruined hall, your head pounding and your armor gone. The air reeks of smoke, iron, and old blood.

Faint torchlight flickers across toppled pillars and shattered glass — the remnants of the old sanctum where you had just retrieved the Heart of Radiance, a sacred relic.

You remember now: the attack came at dusk. A pack of goblin bandits ambushed you, stole your gear, shattered your enchanted map, and stole the Heart of Radiance... then left you for dead.

Without the map's guiding spell, the sanctum's halls — once woven with radiant wards to conceal the relic — now twist and shift at random. Each step forward reshapes the labyrinth anew.

Echoing goblin screams from the labyrinth below tell you where they fled to hide, but in doing so, they awakened creatures far worse.

Weak but alive, you feel the quiet warmth of your connection to the Light. It has not abandoned you. Not yet."""
        self.storyteller.track_event("game_start", opening_text)
        # Clear terminal and show opening narrative
        ui.clear_terminal()
        ui.display_narrative_panel(opening_text, mode="exploration")
        ui.render_status(self.player)  # Initial status in exploration mode
        while self.player.is_alive() and not self.game_won:
            if self.current_monster is None:
                self._exploration_phase()
                # After exploration phase, show exploration status
                ui.render_status(self.player)
            else:
                self._combat_phase()
                # After combat phase, show appropriate status based on whether combat continues
                if self.current_monster is not None:
                    ui.render_status(self.player, mode="combat", enemy=self.current_monster)
                else:
                    ui.render_status(self.player)  # Back to exploration after combat ends
        if self.game_won:
            victory_text = "The last foe falls; somewhere, an exit reveals itself."
            self.storyteller.track_event("game_victory", victory_text)
            print(victory_text, flush=True)

    # =====================
    # Safe / Pre-combat
    # =====================
    def _exploration_phase(self) -> None:
        action_options: List[ActionOption] = [
            ActionOption("Proceed onward", "proceed")
        ]
        if self.player.health < self.player.max_health:
            action_options.append(ActionOption("Pray for restoration (full heal)", "pray"))
        option_labels = [option.display_label for option in action_options]
        selected_index = ui.prompt_choice("📜 Choose your course:", option_labels)
        action_choice = action_options[selected_index].action_id
        if action_choice == "proceed":
            self._explore_room()
        elif action_choice == "pray":
            self._generate_narrative(
                lambda: self.storyteller.describe_pray(self.player),
                None,  # Don't track prayer as a significant event
                "exploration"
            )
            self.player.pray_for_restoration()
        elif action_choice == "potion":
            self._generate_narrative(
                lambda: self.storyteller.describe_potion_use(self.player),
                None,  # Don't track potion use as a significant event
                "exploration"
            )
        else:
            raise ValueError(f"Invalid selection: {action_choice}")

    def _explore_room(self) -> None:
        ui.print_debug("_explore_room", "_has_all_gear = " + str(self._has_all_gear()))
        ui.print_debug("_explore_room", "monsters_defeated = " + str(self.monsters_defeated))
        ui.print_debug("_explore_room", "BOSS_SPAWN_THRESHOLD = " + str(config.BOSS_SPAWN_THRESHOLD))
        ui.print_debug("_explore_room", "BOSS_SPAWN_CHANCE = " + str(config.BOSS_SPAWN_CHANCE))
        room_type = self._select_random_room_type()
        if room_type == RoomType.EMPTY.value:
            self._generate_narrative(
                lambda: self.storyteller.describe_empty_room(),
                None,  # Don't track empty rooms as significant events
                "exploration"
            )
            return
        if room_type == RoomType.LOOT.value:
            drop = self.drop_calculator.roll_item_drop(self.player)
            # Generate narrative description of finding the loot
            def get_loot_description():
                if drop == DropResult.NO_ITEM:
                    return self.storyteller.describe_empty_room()
                return self.storyteller.describe_loot_find(drop, self.player)

            self._generate_narrative(
                get_loot_description,
                "loot",
                "exploration"
            )
            # Apply the loot after showing the description
            self._apply_loot(drop)
            return
        # Monster room
        # Get the drop for this monster
        # Small chance to encounter the boss after some progress
        if self.monsters_defeated >= config.BOSS_SPAWN_THRESHOLD and self.random_provider.random() < config.BOSS_SPAWN_CHANCE:
            self.current_monster = self.monster_generator.generate_boss()
        else:
            self.current_monster = self.monster_generator.generate_monster()
        # Store the drop on the monster
        drop = self.drop_calculator.get_drop_for_monster(self.monsters_defeated, self.player)
        self.current_monster.item_drop = drop
        # Generate full narrative encounter description from LLM
        self._generate_narrative(
            lambda: self.storyteller.describe_encounter(
                self.current_monster.name,
                self.current_monster.description,
                drop if drop != DropResult.NO_ITEM else None,
                self.player
            ),
            "encounter",
            "combat"
        )

    def _select_random_room_type(self) -> str:
        room_type_weights = config.ROOM_TYPE_WEIGHTS

        # Create RoomTypeOption instances
        room_options = [
            RoomTypeOption(RoomType(room_name), room_weight)
            for room_name, room_weight in room_type_weights.items()
        ]

        # Convert to WeightedOption for selection
        weighted_options = [
            WeightedOption(room_option.room_type.value, room_option.spawn_weight)
            for room_option in room_options
        ]

        return select_weighted_random(weighted_options, self.random_provider)

    # =====================
    # Combat
    # =====================
    def _combat_phase(self) -> None:
        assert self.current_monster is not None
        while self.player.is_alive() and self.current_monster.is_alive():
            available_actions = self._get_available_combat_actions()
            action_labels = [self._get_action_label(action) for action in available_actions]
            selected_index = ui.prompt_choice("⚔️ In battle, choose your action:", action_labels)
            selected_action = available_actions[selected_index]
            if selected_action == Action.USE_POTION:
                self._generate_narrative(
                    lambda: self.storyteller.describe_potion_use(self.player),
                    None,  # Don't track potion use as a significant event
                    "combat"
                )
            elif selected_action == Action.FLEE:
                flee_succeeded = self.player.attempt_flee(self.random_provider.random)
                self._generate_narrative(
                    lambda: self.storyteller.describe_flee(flee_succeeded, self.current_monster.name),
                    "flee",
                    "combat"
                )
                if flee_succeeded:
                    self.current_monster = None
                    return
            else:
                # Combat action (Holy Smite, Shield Bash, Sword Slash)
                ability_map = self.player.abilities()
                base_damage = ability_map[selected_action]()
                final_damage = self._calculate_player_damage(selected_action, self.current_monster)
                # Check if it's a weakness hit
                matching_weakness = self.ACTION_TO_WEAKNESS.get(selected_action)
                is_weakness = (matching_weakness is not None and
                              matching_weakness in self.current_monster.weaknesses and
                              final_damage > base_damage)
                # Apply player damage
                damage_dealt = self.current_monster.take_damage(final_damage)
                monster_died = not self.current_monster.is_alive()

                # Handle monster retaliation if it survived
                monster_retaliation_damage = None
                player_health_after = None
                if not monster_died:
                    monster_attack_damage = self.current_monster.attack()
                    monster_retaliation_damage = self.player.take_damage(monster_attack_damage, defense=self.player.get_defense())
                    player_health_after = self.player.health

                # Generate single narrative for the complete combat turn
                if monster_died:
                    # If monster died, let victory handle the narrative (includes the killing blow)
                    self.monsters_defeated += 1
                    self._handle_monster_defeat(self.current_monster, selected_action, is_weakness)
                    self.current_monster = None
                    return
                else:
                    # Monster survived - describe the complete turn (player action + monster retaliation)
                    self._generate_narrative(
                        lambda: self.storyteller.describe_combat_turn(
                            self._get_action_label(selected_action),
                            self.current_monster.name,
                            self.current_monster.description,
                            damage_dealt,
                            is_weakness,
                            self.player,
                            monster_retaliation_damage=monster_retaliation_damage,
                            player_health_after=player_health_after
                        ),
                        "combat",
                        "combat"
                    )
            if self.player.is_alive():
                ui.render_status(self.player, mode="combat", enemy=self.current_monster)

    def _get_available_combat_actions(self) -> List[Action]:
        options: List[Action] = list(self.player.abilities().keys())
        # Only show potion option if player is injured AND has potions
        if self.player.health < self.player.max_health and self.player.inventory.num_potions > 0:
            options.append(Action.USE_POTION)
        options.append(Action.FLEE)
        return options

    def _get_action_label(self, action: Action) -> str:
        action_labels = {
            Action.HOLY_SMITE: "Holy Smite",
            Action.SWORD_SLASH: "Sword Slash",
            Action.SHIELD_BASH: "Shield Bash",
            Action.USE_POTION: "Use Potion",
            Action.FLEE: "Flee",
        }
        return action_labels[action]

    def _calculate_player_damage(self, action: Action, monster: Monster) -> int:
        ability_map = self.player.abilities()
        dmg_fn = ability_map.get(action)
        if dmg_fn is None:
            return 0
        base = dmg_fn()
        return monster.apply_weakness_bonus(action, base)

    def _handle_monster_defeat(self, monster: Monster, final_action: Optional[Action] = None, is_weakness: bool = False) -> None:
        """Handle monster defeat: victory narration and loot rewards.

        Args:
            monster: The defeated monster
            final_action: The action that killed the monster
            is_weakness: Whether the final action was a weakness hit
        """
        item_name = self._format_item_name(monster.item_drop)

        # If we know the final action, include it in the victory description
        action_label = self._get_action_label(final_action) if final_action else None

        self._generate_narrative(
            lambda: self.storyteller.describe_victory(
                monster.name,
                monster.description,
                item_name,
                self.player,
                final_action=action_label,
                is_weakness=is_weakness
            ),
            "victory",
            "combat"
        )

        # If boss is defeated, end the run with victory.
        if monster.is_boss:
            self.game_won = True
            return
        # Apply the drop that was determined when the monster was encountered
        # (fallback to rolling if somehow drop wasn't set, though this shouldn't happen)
        drop = monster.item_drop if monster.item_drop is not None else self.drop_calculator.roll_item_drop(self.player)
        self._apply_loot(drop)

    def _has_all_gear(self) -> bool:
        ui.print_debug("_has_all_gear", "player.has_shield = " + str(self.player.has_shield))
        ui.print_debug("_has_all_gear", "player.has_sword = " + str(self.player.has_sword))
        ui.print_debug("_has_all_gear", "self.player.owned_armor = " + str(self.player.owned_armor))
        """Check if the player has recovered all their stolen gear."""
        all_gear = DropResult.unique_gear()
        if not self.player.has_shield or not self.player.has_sword:
            return False
        # Check if player has all 6 armor pieces
        armor_pieces = [item for item in all_gear if item not in (DropResult.SHIELD, DropResult.SWORD)]
        return len(self.player.owned_armor) == len(armor_pieces)

    def _apply_loot(self, drop: DropResult) -> None:
        """Apply loot to player and show unlock messages if needed."""
        if drop == DropResult.NO_ITEM:
            return

        # Handle consumables with a mapping
        consumable_handlers = {
            DropResult.HEALTH_POTION: lambda: self.player.inventory.add_potion(),
            DropResult.ESCAPE_SCROLL: lambda: self.player.inventory.add_escape_scroll(),
        }
        if drop in consumable_handlers:
            consumable_handlers[drop]()
            return

        # Handle unique ability unlocks
        if drop == DropResult.SHIELD:
            self.player.has_shield = True
            print("Shield Bash unlocked! 🛡️", flush=True)
            return
        if drop == DropResult.SWORD:
            self.player.has_sword = True
            print("Sword Slash unlocked! 🗡️", flush=True)
            return

        # Handle armor pieces
        was_complete_before = self._has_all_gear()
        self.player.add_armor_piece(drop)
        if not was_complete_before and self._has_all_gear():
            self._generate_narrative(
                lambda: self.storyteller.describe_all_gear_recovered(self.player),
                None,
                "exploration"
            )
