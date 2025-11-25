from __future__ import annotations

from typing import List, Optional, Protocol

import config
from combat_engine import CombatEngine
from drop_calculator import DropCalculator
from monster_generator import MonsterGenerator
from narrative_engine import NarrativeEngine
import ui
from models import (
    ActionOption,
    DropResult,
    Monster,
    Player,
    RoomType,
    RoomTypeOption,
    WeightedOption,
)
from utils import RandomProvider, DefaultRandomProvider, select_weighted_random

# Enables the game to use different storytellers (e.g., for testing) without changing the game code
class StoryTellerProtocol(Protocol):
    # OO rationale: Behavioral contract for narrative providers. Allows the
    # game loop to depend on an interface instead of a concrete type.
    def track_event(self, event_type: str, description: str) -> None: ...

class GameEngine:
    # OO rationale: Orchestrator and state machine for the game flow. It
    # coordinates services (storyteller, RNG, generators) and owns session
    # state (player, current monster). Keeps domain logic cohesive while
    # delegating specialized behavior to collaborators.
    """Main orchestrator for exploration and combat."""

    def __init__(self, storyteller: StoryTellerProtocol) -> None:
        """Initialize GameSystem with a StoryTeller (required).

        Args:
            storyteller: StoryTeller implementation (typically LLMStoryTeller)
        """
        self.storyteller: StoryTellerProtocol = storyteller
        self.narrative_engine = NarrativeEngine(storyteller)
        self.random_provider: RandomProvider = DefaultRandomProvider()
        self.combat_engine = CombatEngine(self.narrative_engine, self.random_provider)
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


    def start_game(self) -> None:
        opening_text = self.narrative_engine.narrate_opening()
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
            victory_text = self.narrative_engine.describe_victory_ending()
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
            self.narrative_engine.describe_prayer(self.player)
            self.player.pray_for_restoration()
        elif action_choice == "potion":
            self.narrative_engine.describe_potion_use(self.player, "exploration")
        else:
            raise ValueError(f"Invalid selection: {action_choice}")

    def _explore_room(self) -> None:
        ui.print_debug("_explore_room", "monsters_defeated = " + str(self.monsters_defeated))
        room_type = self._select_random_room_type()
        if room_type == RoomType.EMPTY.value:
            self.narrative_engine.describe_empty_room()
            return
        if room_type == RoomType.LOOT.value:
            drop = self.drop_calculator.roll_item_drop(self.player)
            self.narrative_engine.describe_loot_find(drop, self.player)
            # Apply the loot after showing the description
            self._apply_loot(drop)
            return
        # Monster room
        self.current_monster = self.monster_generator.generate_monster(self.monsters_defeated)
        self.current_monster.item_drop = self.drop_calculator.get_drop_for_monster(self.monsters_defeated, self.player)
        self.narrative_engine.describe_encounter(self.current_monster, self.player)

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

        # Run combat using the combat engine
        combat_result = self.combat_engine.run_combat_phase(self.player, self.current_monster)

        # Process combat result
        if combat_result.monster_was_defeated:
            # Monster was defeated
            self.monsters_defeated += 1
            game_should_end = self.combat_engine.handle_monster_defeat(
                combat_result.defeated_monster,
                self.player,
                final_action=combat_result.final_action,
                is_weakness=combat_result.was_weakness_hit
            )
            if game_should_end:
                self.game_won = True

            self._apply_loot(combat_result.defeated_monster.item_drop)

        # Clear current monster (combat ended)
        self.current_monster = None


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
            self.narrative_engine.describe_all_gear_recovered(self.player)
