from __future__ import annotations

import random
from typing import List, Optional, Tuple, Protocol, Any, Union, Callable

import config
import ui
from models import (
    Action,
    DropResult,
    Monster,
    Player,
    Weakness,
)


class StoryTellerProtocol(Protocol):
    # OO rationale: Behavioral contract for narrative providers. Allows the
    # game loop to depend on an interface instead of a concrete type.
    def get_current_description(self, context: str) -> str: ...
    def describe_item_in_context(self, item: Union[DropResult, str], monster_name: str, monster_description: str) -> str: ...

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

def pick_weighted(buckets: List[Tuple[str, float]], random_provider: RandomProvider) -> str:
    # OO rationale: Centralized, pure utility that implements weighted selection.
    # - Single-responsibility: callers (loot, rooms) don't duplicate probability logic.
    # - Dependency inversion: consumes RandomProvider to remain deterministic in tests.
    # - Decoupling: returns a label, letting each subsystem map labels to domain types.
    total_weight = sum(weight for _, weight in buckets)
    if total_weight <= 0:
        return buckets[-1][0]
    random_threshold = random_provider.random() * total_weight
    running_total = 0.0
    for label, weight in buckets:
        running_total += weight
        if random_threshold <= running_total:
            return label
    return buckets[-1][0]

class MonsterGenerator:
    # OO rationale: Factory responsible for building fully-formed Monster
    # instances from templates. Centralizes variability (names, stats,
    # weaknesses) and keeps creation logic out of the game loop.
    """Generates a single monster from a simple in-memory table."""

    def __init__(self, random_provider: RandomProvider) -> None:
        self.random_provider = random_provider
        self._templates = [
            # Regular foes
            {
                "name": "Skeleton",
                "weaknesses": [Weakness.HOLY_SMITE, Weakness.SHIELD_BASH],
                "description": "A humanoid frame of loose bones held by brittle bindings; light, rattling steps and hollow gaze.",
            },
            {
                "name": "Goblin Bandit",
                "weaknesses": [Weakness.SWORD_SLASH, Weakness.SHIELD_BASH],
                "description": "A small, agile greenskin with oversized ears and quick hands; favors scavenged gear and sudden lunges.",
            },
            {
                "name": "Giant Rat",
                "weaknesses": [Weakness.SWORD_SLASH],
                "description": "An oversized rat with patchy fur and prominent incisors; jittery, low to the ground, always testing distance.",
            },
            {
                "name": "Wraith",
                "weaknesses": [Weakness.HOLY_SMITE],
                "description": "A dim, humanoid outline woven from chill mist; light fades and warmth thins in its presence.",
            },
        ]

    def generate_monster(self) -> Monster:
        monster_template = self.random_provider.choice(self._templates)
        max_health_points = monster_template.get("hp") or self.random_provider.randint(
            config.MONSTER_HEALTH_MIN, config.MONSTER_HEALTH_MAX
        )
        attack_strength = monster_template.get("strength") or self.random_provider.randint(
            config.MONSTER_STRENGTH_MIN, config.MONSTER_STRENGTH_MAX
        )
        return Monster(
            max_health=max_health_points,
            strength=attack_strength,
            name=monster_template["name"],
            weaknesses=list(monster_template["weaknesses"]),
            description=monster_template["description"],
            is_boss=bool(monster_template.get("is_boss", False)),
        )

    def generate_boss(self) -> Monster:
        # Single end-of-run boss
        boss_template = {
            "name": "Grave Tyrant",
            "weaknesses": [Weakness.HOLY_SMITE, Weakness.SWORD_SLASH],
            "description": (
                "An armored lich-king draped in funereal banners. A corroded crown sits on a skull carved with runes; "
                "a great blade of black iron rests across its lap. Plates of ornate mail are missing in places, "
                "revealing ribs choked with grave dust."
            ),
            "hp": config.BOSS_HP,
            "strength": config.BOSS_STRENGTH,
            "is_boss": True,
        }
        return Monster(
            max_health=boss_template["hp"],
            strength=boss_template["strength"],
            name=boss_template["name"],
            weaknesses=list(boss_template["weaknesses"]),
            description=boss_template["description"],
            is_boss=True,
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
        return self.roll_item_drop()

    def roll_item_drop(self) -> DropResult:
        """Roll for a random item drop, excluding unique items that have already been dropped."""
        # Build base weights
        weight_no_item = config.DROP_WEIGHTS["NO_ITEM"]
        weight_health_potion = config.DROP_WEIGHTS["HEALTH_POTION"]
        weight_escape_scroll = config.DROP_WEIGHTS["ESCAPE_SCROLL"]
        # Check if any gear (armor pieces) remain
        # Filter _remaining_gear to get only armor pieces (exclude shield and sword)
        remaining_armor = [item for item in self._remaining_gear if item not in (DropResult.SHIELD, DropResult.SWORD)]
        weight_armor = config.DROP_WEIGHTS["ARMOR"] if remaining_armor else 0.0

        # If no armor remains, redistribute armor weight to 'no item'
        if not remaining_armor:
            weight_no_item += config.DROP_WEIGHTS["ARMOR"]

        # Armor selection is two-step: pick 'armor' bucket, then pick which piece
        buckets: List[Tuple[str, float]] = [
            ("NO_ITEM", weight_no_item),
            ("HEALTH_POTION", weight_health_potion),
            ("ESCAPE_SCROLL", weight_escape_scroll),
            ("ARMOR", weight_armor),
        ]
        chosen_bucket = pick_weighted(buckets, self.random_provider)

        if chosen_bucket == "NO_ITEM":
            return DropResult.NO_ITEM
        if chosen_bucket == "HEALTH_POTION":
            return DropResult.HEALTH_POTION
        if chosen_bucket == "ESCAPE_SCROLL":
            return DropResult.ESCAPE_SCROLL
        if chosen_bucket == "ARMOR" and remaining_armor:
            armor_piece = self.random_provider.choice(remaining_armor)
            self._remaining_gear.remove(armor_piece)
            return armor_piece
        return DropResult.NO_ITEM

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
        self.player.health = 10
        self.current_monster: Optional[Monster] = None
        self.drop_calculator = DropCalculator(self.random_provider)
        self.monster_generator = MonsterGenerator(self.random_provider)
        self.defeated_monsters_count: int = 0
        self.game_won: bool = False

    def _get_player_equipment_state(self) -> Tuple[bool, bool, bool]:
        """Get player's current equipment state.

        Returns:
            Tuple of (has_shield, has_sword, has_armor)
        """
        return (
            self.player.has_shield,
            self.player.has_sword,
            len(self.player.owned_armor) > 0
        )

    def _call_storyteller_with_loading(
        self,
        storyteller_callable: Callable[[], str],
        prefix: str,
        fallback_text: str
    ) -> None:
        """Helper to call storyteller methods with loading message and error handling.

        Args:
            storyteller_callable: A callable that returns the description string
            prefix: Prefix for the message (e.g., "rest", "potion", "attack")
            fallback_text: Fallback text if the LLM call fails
        """
        print("Story Teller is thinking...", end="", flush=True)
        try:
            description = storyteller_callable()
            print("\r" + " " * 30 + "\r", end="", flush=True)
            ui.show(self.storyteller, f"{prefix}: {description}")
        except Exception as e:
            print()
            print(f"Error generating description: {e}", flush=True)
            ui.show(self.storyteller, f"{prefix}: {fallback_text}")

    def _collect_items_acquired(self, monster: Monster) -> List[str]:
        """Collect all items that will be acquired after defeating a monster.

        Args:
            monster: The monster being defeated

        Returns:
            List of item names (e.g., ["a shield", "health potion"])
        """
        if monster.item_drop is None or monster.item_drop == DropResult.NO_ITEM:
            return []
        # Format shield/sword as "a shield"/"a sword" for narrative consistency
        if monster.item_drop == DropResult.SHIELD:
            return ["a shield"]
        if monster.item_drop == DropResult.SWORD:
            return ["a sword"]
        item_name = monster.item_drop.name.replace("_", " ").lower()
        return [item_name]

    def start_game(self) -> None:
        opening_text = """game:start: You awaken on the cold stone floor of a ruined hall, your head pounding and your armor gone. The air reeks of smoke, iron, and old blood.

Faint torchlight flickers across toppled pillars and shattered glass — the remnants of the old sanctum where you had just retrieved the **Heart of Radiance**, a sacred relic.

You remember now: the attack came at dusk. A pack of goblin bandits ambushed you, stole your gear, shattered your enchanted map, and stole the **Heart of Radiance**... then left you for dead.

Without the map's guiding spell, the sanctum's halls — once woven with radiant wards to conceal the relic — now twist and shift at random. Each step forward reshapes the labyrinth anew.

Echoing goblin screams from the labyrinth below tell you where they fled to hide, but in doing so, they awakened creatures far worse.

Weak but alive, you feel the quiet warmth of your connection to the Light. It has not abandoned you. Not yet."""
        ui.show(self.storyteller, opening_text)
        while self.player.is_alive() and not self.game_won:
            if self.current_monster is None:
                self._safe_phase()
            else:
                self._combat_phase()
        if self.game_won:
            ui.show(self.storyteller, "game:victory: The last foe falls; somewhere, an exit reveals itself.")
        else:
            ui.show(self.storyteller, "game:over: Your journey ends here; the dark grows still.")

    # =====================
    # Safe / Pre-combat
    # =====================
    def _safe_phase(self) -> None:
        status = self._status_text()
        ui.show(self.storyteller, f"status:\n{status}")
        menu: List[Tuple[str, str]] = [("Proceed onward", "proceed")]
        if self.player.health < self.player.max_health:
            menu.append(("Pray for restoration (full heal)", "pray"))
        titles = [title for title, _ in menu]
        idx = ui.prompt_choice(self.storyteller, "Choose your course:", titles)
        selection = menu[idx][1]
        if selection == "proceed":
            self._proceed_to_room()
        elif selection == "pray":
            self.player.pray_for_restoration()
            has_shield, has_sword, has_armor = self._get_player_equipment_state()
            self._call_storyteller_with_loading(
                lambda: self.storyteller.describe_pray(
                    has_shield=has_shield,
                    has_sword=has_sword,
                    has_armor=has_armor
                ),
                "rest",
                "You pause to recover; breath steadies and wounds close."
            )
        else:  # "potion"
            if self.player.use_potion():
                self._call_storyteller_with_loading(
                    lambda: self.storyteller.describe_potion_use(True),
                    "potion",
                    "You use a potion and restore full health."
                )
            else:
                description = self.storyteller.describe_potion_use(False)
                ui.show(self.storyteller, f"potion: {description}")

    def _proceed_to_room(self) -> None:
        room = self._weighted_room_choice()
        if room == "empty":
            print("Story Teller is thinking...", end="", flush=True)
            try:
                description = self.storyteller.describe_empty_room()
                print("\r" + " " * 30 + "\r", end="", flush=True)
                ui.show(self.storyteller, f"room: {description}")
            except Exception as e:
                print()
                print(f"Error generating description: {e}", flush=True)
                ui.show(self.storyteller, "room: A quiet space—no immediate threats or finds.")
            return
        if room == "loot":
            drop = self.drop_calculator.roll_item_drop()
            # Generate narrative description of finding the loot
            has_shield, has_sword, has_armor = self._get_player_equipment_state()
            print("Story Teller is thinking...", end="", flush=True)
            try:
                description = self.storyteller.describe_loot_find(
                    drop,
                    has_shield=has_shield,
                    has_sword=has_sword,
                    has_armor=has_armor
                )
                print("\r" + " " * 30 + "\r", end="", flush=True)
                ui.show(self.storyteller, f"loot: {description}")
            except Exception as e:
                print()
                print(f"Error generating description: {e}", flush=True)
                # Fallback to simple message
                if drop == DropResult.NO_ITEM:
                    ui.show(self.storyteller, "loot: No notable items found.")
                else:
                    item_name = drop.name.replace("_", " ").title() if drop != DropResult.SHIELD and drop != DropResult.SWORD else drop.name.replace("_", " ").title()
                    ui.show(self.storyteller, f"loot: Found {item_name}.")
            # Apply the loot after showing the description
            self._apply_loot_silent(drop)
            return
        # Monster room
        # Get the drop for this monster
        drop = self.drop_calculator.get_drop_for_monster(self.defeated_monsters_count, self.player)
        # Small chance to encounter the boss after some progress
        if self.defeated_monsters_count >= config.BOSS_SPAWN_THRESHOLD and self.random_provider.random() < config.BOSS_SPAWN_CHANCE:
            self.current_monster = self.monster_generator.generate_boss()
        else:
            self.current_monster = self.monster_generator.generate_monster()
        # Store the drop on the monster
        self.current_monster.item_drop = drop
        # Generate full narrative encounter description from LLM
        print("Story Teller is thinking...", end="", flush=True)
        try:
            description = self.storyteller.describe_encounter(
                self.current_monster.name,
                self.current_monster.description,
                drop if drop != DropResult.NO_ITEM else None
            )
            print("\r" + " " * 30 + "\r", end="", flush=True)
        except Exception as e:
            print()
            print(f"Error generating description: {e}", flush=True)
            import traceback
            traceback.print_exc()
            description = f"You encounter {self.current_monster.name}. {self.current_monster.description}"
        ui.show(self.storyteller, f"encounter: {description}")

    def _weighted_room_choice(self) -> str:
        room_type_weights = config.ROOM_TYPE_WEIGHTS
        buckets = [(room_name, room_weight) for room_name, room_weight in room_type_weights.items()]
        return pick_weighted(buckets, self.random_provider)

    # =====================
    # Combat
    # =====================
    def _combat_phase(self) -> None:
        assert self.current_monster is not None
        while self.player.is_alive() and self.current_monster.is_alive():
            combat_options = self._combat_options()
            option_titles = [self._action_label(action) for action in combat_options]
            selected_index = ui.prompt_choice(self.storyteller, "In battle, choose your action:", option_titles)
            chosen = combat_options[selected_index]
            if chosen == Action.USE_POTION:
                if self.player.use_potion():
                    self._call_storyteller_with_loading(
                        lambda: self.storyteller.describe_potion_use(True),
                        "potion",
                        "You use a potion and restore full health."
                    )
                else:
                    description = self.storyteller.describe_potion_use(False)
                    ui.show(self.storyteller, f"potion: {description}")
            elif chosen == Action.FLEE:
                success = self.player.attempt_flee(self.random_provider.random)
                self._call_storyteller_with_loading(
                    lambda: self.storyteller.describe_flee(success, self.current_monster.name),
                    "flee",
                    "You disengage and escape." if success else "You fail to break away."
                )
                if success:
                    self.current_monster = None
                    return
            else:
                # Combat action (Holy Smite, Shield Bash, Sword Slash)
                ability_map = self.player.abilities()
                base_damage = ability_map[chosen]()
                damage_amount = self._calculate_player_damage(chosen, self.current_monster)
                # Check if it's a weakness hit
                weakness_for_action = self.ACTION_TO_WEAKNESS.get(chosen)
                is_weakness = (weakness_for_action is not None and
                              weakness_for_action in self.current_monster.weaknesses and
                              damage_amount > base_damage)
                # Apply player damage
                damage_taken = self.current_monster.take_damage(damage_amount)
                monster_died = not self.current_monster.is_alive()

                # Handle monster retaliation if it survived
                monster_retaliation_damage = None
                player_health_after = None
                if not monster_died:
                    incoming = self.current_monster.attack()
                    monster_retaliation_damage = self.player.take_damage(incoming, defense=self.player.get_defense())
                    player_health_after = self.player.health

                has_shield, has_sword, has_armor = self._get_player_equipment_state()

                # Generate single narrative for the complete combat turn
                if monster_died:
                    # If monster died, let victory handle the narrative (includes the killing blow)
                    self.defeated_monsters_count += 1
                    self._post_fight_rewards(self.current_monster, chosen, is_weakness)
                    self.current_monster = None
                    return
                else:
                    # Monster survived - describe the complete turn (player action + monster retaliation)
                    self._call_storyteller_with_loading(
                        lambda: self.storyteller.describe_combat_turn(
                            self._action_label(chosen),
                            self.current_monster.name,
                            self.current_monster.description,
                            damage_taken,
                            is_weakness,
                            monster_died=False,
                            monster_retaliation_damage=monster_retaliation_damage,
                            player_health_after=player_health_after,
                            has_shield=has_shield,
                            has_sword=has_sword,
                            has_armor=has_armor
                        ),
                        "combat",
                        f"Your {self._action_label(chosen).lower()} strikes for {damage_taken} damage. The enemy attacks for {monster_retaliation_damage} damage."
                    )

    def _combat_options(self) -> List[Action]:
        options: List[Action] = list(self.player.abilities().keys())
        # Only show potion option if player is injured AND has potions
        if self.player.health < self.player.max_health and self.player.inventory.num_potions > 0:
            options.append(Action.USE_POTION)
        options.append(Action.FLEE)
        return options

    def _action_label(self, action: Action) -> str:
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

    def _post_fight_rewards(self, monster: Monster, final_action: Optional[Action] = None, is_weakness: bool = False) -> None:
        """Handle post-fight rewards and victory narration.

        Args:
            monster: The defeated monster
            final_action: The action that killed the monster
            is_weakness: Whether the final action was a weakness hit
        """
        items_acquired = self._collect_items_acquired(monster)
        has_shield, has_sword, has_armor = self._get_player_equipment_state()

        # If we know the final action, include it in the victory description
        action_label = self._action_label(final_action) if final_action else None

        self._call_storyteller_with_loading(
            lambda: self.storyteller.describe_victory(
                monster.name,
                monster.description,
                items_acquired,
                has_shield=has_shield,
                has_sword=has_sword,
                has_armor=has_armor,
                final_action=action_label,
                is_weakness=is_weakness
            ),
            "victory",
            "Enemy defeated."
        )

        # If boss is defeated, end the run with victory.
        if monster.is_boss:
            self.game_won = True
            return
        # Apply the drop that was determined when the monster was encountered
        # (fallback to rolling if somehow drop wasn't set, though this shouldn't happen)
        drop = monster.item_drop if monster.item_drop is not None else self.drop_calculator.roll_item_drop()
        self._apply_loot(drop)

    def _apply_loot_silent(self, drop: DropResult) -> None:
        """Apply loot to player"""
        if drop == DropResult.NO_ITEM:
            pass  # Nothing to apply
        elif drop == DropResult.HEALTH_POTION:
            self.player.inventory.add_potion()
        elif drop == DropResult.ESCAPE_SCROLL:
            self.player.inventory.add_escape_scroll()
        elif drop == DropResult.SHIELD:
            self.player.has_shield = True
            ui.show(self.storyteller, "loot: Shield Bash unlocked")
        elif drop == DropResult.SWORD:
            self.player.has_sword = True
            ui.show(self.storyteller, "loot: Sword Slash unlocked")
        else:
            self.player.add_armor_piece(drop)

    def _apply_loot(self, drop: DropResult) -> None:
        """Apply loot to player and show narrative message (for post-combat loot)."""
        # For post-combat loot, include it in the victory description, so we just apply silently
        # and show unlock messages if needed
        if drop == DropResult.NO_ITEM:
            pass  # Nothing to apply
        elif drop == DropResult.HEALTH_POTION:
            self.player.inventory.add_potion()
        elif drop == DropResult.ESCAPE_SCROLL:
            self.player.inventory.add_escape_scroll()
        elif drop == DropResult.SHIELD:
            self.player.has_shield = True
            ui.show(self.storyteller, "loot: Shield Bash unlocked")
        elif drop == DropResult.SWORD:
            self.player.has_sword = True
            ui.show(self.storyteller, "loot: Sword Slash unlocked")
        else:
            self.player.add_armor_piece(drop)

    def _status_text(self) -> str:
        hp = f"HP {self.player.health}/{self.player.max_health}"
        defense = f"Defense {self.player.get_defense()}"
        pots = f"Potions {self.player.inventory.num_potions}"
        scrolls = f"Escape Scrolls {self.player.inventory.num_escape_scrolls}"
        abilities = ["Holy Smite"]
        if self.player.has_shield:
            abilities.append("Shield Bash")
        if self.player.has_sword:
            abilities.append("Sword Slash")
        abilities_str = "Abilities: " + ", ".join(abilities)
        return f"{hp} | {defense} | {pots} | {scrolls}\n{abilities_str}"
