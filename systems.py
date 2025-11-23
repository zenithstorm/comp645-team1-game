from __future__ import annotations

import random
from typing import List, Optional, Tuple, Protocol, Any, Union

from . import config, ui
from .models import (
    Action,
    DropResult,
    Monster,
    Player,
    Weakness,
)


class StoryTeller:
    # OO rationale: Adapter over a narrative generator. Kept as a class to allow
    # polymorphic replacement (e.g., real LLM client). Conforms to a protocol,
    # enabling dependency injection and test doubles.
    """Stub that decorates structured context into lightweight prose."""

    def get_current_description(self, context: str) -> str:
        # Minimal decoration to keep it simple; swapping this out for a real LLM later should be trivial.
        prefix = "⟢ "
        suffix = " ⟣"
        return f"{prefix}{context.strip()}{suffix}"

    def describe_item_in_context(self, item: Union[DropResult, str], monster_name: str, monster_type: str, monster_description: str) -> str:
        """Generate a creative description of how the item relates to the monster.

        Args:
            item: Either a DropResult enum (for regular drops) or a string (for unlock items like "a shield")
            monster_name: Name of the monster
            monster_type: Type of the monster
            monster_description: Base description of the monster

        Returns:
            A creative description of how the item appears in relation to the monster.
            Empty string if item is NO_ITEM or invalid.
        """
        # Stub implementation - in production, this would call an LLM with context
        # The LLM will receive: monster_name, monster_type, monster_description, and item
        # and generate creative prose about how the item appears in relation to the monster
        # e.g., A goblin may brandish the player's holy shield at the player
        # e.g., "Your sword rests on the cold stone below, untouched—the wraith clearly slew the bandit who carried it without caring for earthly spoils"

        # Handle DropResult enum
        if isinstance(item, DropResult):
            if item == DropResult.NO_ITEM:
                return ""
            item_name = item.name.replace("_", " ").lower()
        # Handle string (for unlock items)
        elif isinstance(item, str):
            item_name = item
        else:
            return ""

        # Simple placeholder - LLM will generate more creative descriptions based on monster type
        return f" You notice {item_name} nearby."

class StoryTellerProtocol(Protocol):
    # OO rationale: Behavioral contract for narrative providers. Allows the
    # game loop to depend on an interface instead of a concrete type.
    def get_current_description(self, context: str) -> str: ...
    def describe_item_in_context(self, item: Union[DropResult, str], monster_name: str, monster_type: str, monster_description: str) -> str: ...

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
                "type": "Undead",
                "weaknesses": [Weakness.HOLY_SMITE, Weakness.SHIELD_BASH],
                "description": "A humanoid frame of loose bones held by brittle bindings; light, rattling steps and hollow gaze.",
            },
            {
                "name": "Goblin",
                "type": "Greenskin",
                "weaknesses": [Weakness.SWORD_SLASH, Weakness.SHIELD_BASH],
                "description": "A small, agile greenskin with oversized ears and quick hands; favors scavenged gear and sudden lunges.",
            },
            {
                "name": "Cultist",
                "type": "Humanoid",
                "weaknesses": [Weakness.HOLY_SMITE, Weakness.SWORD_SLASH],
                "description": "A robed devotee marked with forbidden symbols; ritual trappings and a fervent, unblinking focus.",
            },
            {
                "name": "Giant Rat",
                "type": "Beast",
                "weaknesses": [Weakness.SWORD_SLASH],
                "description": "An oversized rat with patchy fur and prominent incisors; jittery, low to the ground, always testing distance.",
            },
            {
                "name": "Wraith",
                "type": "Spirit",
                "weaknesses": [Weakness.HOLY_SMITE],
                "description": "A dim, humanoid outline woven from chill mist; light fades and warmth thins in its presence.",
            },
            {
                "name": "Bandit",
                "type": "Humanoid",
                "weaknesses": [Weakness.SHIELD_BASH, Weakness.SWORD_SLASH],
                "description": "A humanoid raider in mismatched leathers with improvised arms; practiced stance and watchful eyes.",
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
            type=monster_template["type"],
            weaknesses=list(monster_template["weaknesses"]),
            description=monster_template["description"],
            is_boss=bool(monster_template.get("is_boss", False)),
        )

    def generate_boss(self) -> Monster:
        # Single end-of-run boss
        boss_template = {
            "name": "Grave Tyrant",
            "type": "Boss",
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
            type=boss_template["type"],
            weaknesses=list(boss_template["weaknesses"]),
            description=boss_template["description"],
            is_boss=True,
        )


class DropCalculator:
    # OO rationale: Encapsulates loot rules and unique item availability.
    # This isolates drop probability and uniqueness constraints from combat
    # flow, making it easy to tune or swap strategies.
    """Handles loot generation with unique armor pieces."""

    def __init__(self, random_provider: RandomProvider) -> None:
        self.random_provider = random_provider
        self._remaining_armor: List[DropResult] = list(DropResult.armor_pieces())

    def roll_item_drop(self) -> DropResult:
        # Build base weights
        weight_no_item = config.DROP_WEIGHTS["NO_ITEM"]
        weight_health_potion = config.DROP_WEIGHTS["HEALTH_POTION"]
        weight_escape_scroll = config.DROP_WEIGHTS["ESCAPE_SCROLL"]
        weight_armor = config.DROP_WEIGHTS["ARMOR"] if self._remaining_armor else 0.0

        # If no armor remains, redistribute armor weight to 'no item'
        if not self._remaining_armor:
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
        if chosen_bucket == "ARMOR" and self._remaining_armor:
            armor_piece = self.random_provider.choice(self._remaining_armor)
            self._remaining_armor.remove(armor_piece)
            return armor_piece
        return DropResult.NO_ITEM


class Progression:
    # OO rationale: Encapsulates scripted unlock logic based on game progress.
    # Separates progression rules from game orchestration, making unlock
    # conditions easy to modify and test independently.
    """Handles scripted unlocks based on defeated monsters count."""

    def get_pending_unlocks(self, defeated_count: int, player: Player) -> List[str]:
        """Predict what will be unlocked when the next monster is defeated. Returns list of item names."""
        pending: List[str] = []
        next_count = defeated_count + 1
        if next_count == 1 and not player.has_shield:
            pending.append("shield")
        if next_count == 3 and not player.has_sword:
            pending.append("sword")
        return pending

    def check_and_apply_unlocks(self, defeated_count: int, player: Player) -> List[str]:
        """Check unlock conditions and apply them to the player. Returns list of unlock messages."""
        messages: List[str] = []
        if defeated_count == 1 and not player.has_shield:
            player.has_shield = True
            messages.append("loot: Shield acquired. (Shield Bash unlocked)")
        if defeated_count == 3 and not player.has_sword:
            player.has_sword = True
            messages.append("loot: Sword acquired. (Sword Slash unlocked)")
        return messages


class GameSystem:
    # OO rationale: Orchestrator and state machine for the game flow. It
    # coordinates services (storyteller, RNG, generators) and owns session
    # state (player, current monster). Keeps domain logic cohesive while
    # delegating specialized behavior to collaborators.
    """Main orchestrator for exploration and combat."""

    def __init__(self) -> None:
        self.storyteller: StoryTellerProtocol = StoryTeller()
        self.random_provider: RandomProvider = DefaultRandomProvider()
        self.player = Player(
            max_health=config.PLAYER_MAX_HEALTH,
            strength=config.PLAYER_BASE_STRENGTH,
            base_defense=config.PLAYER_BASE_DEFENSE,
        )
        self.current_monster: Optional[Monster] = None
        self.drop_calculator = DropCalculator(self.random_provider)
        self.monster_generator = MonsterGenerator(self.random_provider)
        self.progression = Progression()
        self.defeated_monsters_count: int = 0
        self.game_won: bool = False

    def start_game(self) -> None:
        ui.show(self.storyteller, "game:start: You step past a threshold into shadowed passages.")
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
        menu.append(("Use a health potion", "potion"))
        titles = [title for title, _ in menu]
        idx = ui.prompt_choice(self.storyteller, "Choose your course:", titles)
        selection = menu[idx][1]
        if selection == "proceed":
            self._proceed_to_room()
        elif selection == "pray":
            self.player.pray_for_restoration()
            ui.show(self.storyteller, "rest: You pause to recover; breath steadies and wounds close.")
        else:  # "potion"
            if self.player.use_potion():
                ui.show(self.storyteller, "potion: You drink a vial and feel your strength return to full.")
            else:
                ui.show(self.storyteller, "potion: You check your supplies—no potions remain.")

    def _proceed_to_room(self) -> None:
        room = self._weighted_room_choice()
        if room == "empty":
            ui.show(self.storyteller, "room: A quiet space—no immediate threats or finds.")
            return
        if room == "loot":
            drop = self.drop_calculator.roll_item_drop()
            self._apply_loot(drop, source="room")
            return
        # Monster room
        # Roll the drop now so we can describe it in the encounter
        guaranteed_drop = self.drop_calculator.roll_item_drop()
        # Check what unlocks are pending before generating the monster
        pending_unlocks = self.progression.get_pending_unlocks(self.defeated_monsters_count, self.player)
        # Small chance to encounter the boss after some progress
        if self.defeated_monsters_count >= config.BOSS_SPAWN_THRESHOLD and self.random_provider.random() < config.BOSS_SPAWN_CHANCE:
            self.current_monster = self.monster_generator.generate_boss()
        else:
            self.current_monster = self.monster_generator.generate_monster()
        # Store the guaranteed drop on the monster
        self.current_monster.guaranteed_drop = guaranteed_drop
        # Generate description with item context
        description = self.current_monster.description
        # Add unlock items to description via StoryTeller (these will be acquired after defeat)
        if "shield" in pending_unlocks:
            shield_desc = self.storyteller.describe_item_in_context(
                "a shield", self.current_monster.name, self.current_monster.type, self.current_monster.description
            )
            description += shield_desc
        if "sword" in pending_unlocks:
            sword_desc = self.storyteller.describe_item_in_context(
                "a sword", self.current_monster.name, self.current_monster.type, self.current_monster.description
            )
            description += sword_desc
        # Add regular drop items via StoryTeller
        if guaranteed_drop != DropResult.NO_ITEM:
            item_description = self.storyteller.describe_item_in_context(
                guaranteed_drop, self.current_monster.name, self.current_monster.type, self.current_monster.description
            )
            description += item_description
        ui.show(
            self.storyteller,
            f"encounter: Enemy spotted: {self.current_monster.name} ({self.current_monster.type}). "
            f"{description}",
        )

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
                    ui.show(self.storyteller, "potion: You use a potion and restore full health.")
                else:
                    ui.show(self.storyteller, "potion: No potions available.")
            elif chosen == Action.FLEE:
                success = self.player.attempt_flee(self.rng.random)
                if success:
                    ui.show(self.storyteller, "flee: You disengage and escape.")
                    self.current_monster = None
                    return
                else:
                    ui.show(self.storyteller, "flee: You fail to break away.")
            else:
                damage_amount = self._calculate_player_damage(chosen, self.current_monster)
                damage_taken = self.current_monster.take_damage(damage_amount)
                ui.show(
                    self.storyteller,
                    f"attack: Your {self._action_label(chosen).lower()} strikes for {damage_taken} damage.",
                )
                if not self.current_monster.is_alive():
                    ui.show(self.storyteller, "victory: Enemy defeated.")
                    self.defeated_monsters_count += 1
                    self._post_fight_rewards(self.current_monster)
                    self.current_monster = None
                    return

            # Monster retaliates if still alive
            if self.current_monster and self.current_monster.is_alive():
                incoming = self.current_monster.attack()
                reduced = self.player.take_damage(incoming, defense=self.player.get_defense())
                ui.show(
                    self.storyteller,
                    f"retaliation: The enemy attacks for {reduced} damage.",
                )

    def _combat_options(self) -> List[Action]:
        options: List[Action] = list(self.player.abilities().keys())
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
            Action.PROCEED: "Proceed",
            Action.PRAY: "Pray",
        }
        return action_labels[action]

    def _calculate_player_damage(self, action: Action, monster: Monster) -> int:
        ability_map = self.player.abilities()
        dmg_fn = ability_map.get(action)
        if dmg_fn is None:
            return 0
        base = dmg_fn()
        return monster.apply_weakness_bonus(action, base)

    def _post_fight_rewards(self, monster: Monster) -> None:
        # If boss is defeated, end the run with victory.
        if monster.is_boss:
            ui.show(self.storyteller, "victory: The boss is defeated.")
            self.game_won = True
            return
        # Scripted unlocks
        unlock_messages = self.progression.check_and_apply_unlocks(self.defeated_monsters_count, self.player)
        for message in unlock_messages:
            ui.show(self.storyteller, message)
        # Use the guaranteed drop that was determined when the monster was encountered
        if monster.guaranteed_drop is not None:
            self._apply_loot(monster.guaranteed_drop, source="battle")
        else:
            # Fallback: roll if somehow drop wasn't set (shouldn't happen)
            drop = self.drop_calculator.roll_item_drop()
            self._apply_loot(drop, source="battle")

    def _apply_loot(self, drop: DropResult, source: str) -> None:
        if drop == DropResult.NO_ITEM:
            ui.show(self.storyteller, "loot: No notable items found.")
            return
        if drop == DropResult.HEALTH_POTION:
            self.player.inventory.add_potion()
            ui.show(self.storyteller, "loot: Gained 1 Health Potion.")
            return
        if drop == DropResult.ESCAPE_SCROLL:
            self.player.inventory.add_escape_scroll()
            ui.show(self.storyteller, "loot: Gained 1 Escape Scroll.")
            return
        # Armor piece
        self.player.add_armor_piece(drop)
        piece_name = drop.name.replace("_", " ").title()
        ui.show(self.storyteller, f"loot: Gained armor: {piece_name}.")

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


