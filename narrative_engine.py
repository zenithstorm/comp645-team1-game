"""Narrative generation engine for the dungeon crawler game.

This module handles all narrative text generation, formatting, and display logic.
It acts as a bridge between the game engine and the storyteller, managing
loading indicators, error handling, and item name formatting.
"""

from __future__ import annotations

import sys
from typing import Callable, Optional

import ui
from models import DropResult, Player


class NarrativeEngine:
    """Handles narrative generation, formatting, and display.

    OO rationale: Separates narrative concerns from game logic. This class
    encapsulates all the complexity of generating, formatting, and displaying
    narrative text, including error handling and loading indicators.
    """

    def __init__(self, storyteller) -> None:
        """Initialize the narrative engine with a storyteller.

        Args:
            storyteller: The storyteller implementation (e.g., LLMStoryTeller)
        """
        self.storyteller = storyteller

    def describe_and_narrate(
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
        ui.clear_terminal()

        print("Story Teller is thinking...", end="", flush=True)
        try:
            narrative_text = narrative_generator()
            print("\r" + " " * 30 + "\r", end="", flush=True)
            if event_type:
                self.storyteller.track_event(event_type, narrative_text)
            ui.display_narrative_panel(narrative_text, mode)
        except Exception as e:
            print()
            print(f"Error generating description: {e}", flush=True)
            print("The game cannot continue without the Story Teller. Exiting...", flush=True)
            sys.exit(1)

    def format_item_name(self, item: DropResult) -> Optional[str]:
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

    def narrate_opening(self) -> str:
        """Get the opening narrative text for the game."""
        return """You awaken on the cold stone floor of a ruined hall, your head pounding and your armor gone. The air reeks of smoke, iron, and old blood.

Faint torchlight flickers across toppled pillars and shattered glass — the remnants of the old sanctum where you had just retrieved the Heart of Radiance, a sacred relic.

You remember now: the attack came at dusk. A pack of goblin bandits ambushed you, stole your gear, shattered your enchanted map, and stole the Heart of Radiance... then left you for dead.

Without the map's guiding spell, the sanctum's halls — once woven with radiant wards to conceal the relic — now twist and shift at random. Each step forward reshapes the labyrinth anew.

Echoing goblin screams from the labyrinth below tell you where they fled to hide, but in doing so, they awakened creatures far worse.

Weak but alive, you feel the quiet warmth of your connection to the Light. It has not abandoned you. Not yet."""

    def describe_victory_ending(self) -> str:
        """Get the victory ending text."""
        return "The last foe falls; somewhere, an exit reveals itself."

    # Convenience methods for common narrative generation patterns
    def describe_empty_room(self, mode: str = "exploration") -> None:
        """Generate narrative for an empty room."""
        self.describe_and_narrate(
            lambda: self.storyteller.describe_empty_room(),
            None,  # Don't track empty rooms as significant events
            mode
        )

    def describe_prayer(self, player: Player, mode: str = "exploration") -> None:
        """Generate narrative for prayer/restoration."""
        self.describe_and_narrate(
            lambda: self.storyteller.describe_pray(player),
            None,  # Don't track prayer as a significant event
            mode
        )

    def describe_potion_use(self, player: Player, mode: str = "combat") -> None:
        """Generate narrative for potion use."""
        self.describe_and_narrate(
            lambda: self.storyteller.describe_potion_use(player),
            None,  # Don't track potion use as a significant event
            mode
        )

    def describe_loot_find(self, drop: DropResult, player: Player) -> None:
        """Generate narrative for finding loot."""
        def get_loot_description():
            if drop == DropResult.NO_ITEM:
                return self.storyteller.describe_empty_room()
            return self.storyteller.describe_loot_find(drop, player)

        self.describe_and_narrate(
            get_loot_description,
            "loot",
            "exploration"
        )

    def describe_encounter(self, monster, drop: DropResult, player: Player) -> None:
        """Generate narrative for monster encounter."""
        self.describe_and_narrate(
            lambda: self.storyteller.describe_encounter(
                monster.name,
                monster.description,
                drop if drop != DropResult.NO_ITEM else None,
                player
            ),
            "encounter",
            "combat"
        )

    def describe_flee_attempt(self, succeeded: bool, monster_name: str) -> None:
        """Generate narrative for flee attempt."""
        self.describe_and_narrate(
            lambda: self.storyteller.describe_flee(succeeded, monster_name),
            "flee",
            "combat"
        )

    def describe_combat_turn(self, action_label: str, monster, damage_dealt: int,
                           is_weakness: bool, player: Player,
                           monster_retaliation_damage: Optional[int] = None,
                           player_health_after: Optional[int] = None) -> None:
        """Generate narrative for a complete combat turn."""
        self.describe_and_narrate(
            lambda: self.storyteller.describe_combat_turn(
                action_label,
                monster.name,
                monster.description,
                damage_dealt,
                is_weakness,
                player,
                monster_retaliation_damage=monster_retaliation_damage,
                player_health_after=player_health_after
            ),
            "combat",
            "combat"
        )

    def describe_victory(self, monster, item_name: Optional[str], player: Player,
                        final_action: Optional[str] = None, is_weakness: bool = False) -> None:
        """Generate narrative for monster victory."""
        self.describe_and_narrate(
            lambda: self.storyteller.describe_victory(
                monster.name,
                monster.description,
                item_name,
                player,
                final_action=final_action,
                is_weakness=is_weakness
            ),
            "victory",
            "combat"
        )

    def describe_all_gear_recovered(self, player: Player) -> None:
        """Generate narrative for recovering all gear."""
        self.describe_and_narrate(
            lambda: self.storyteller.describe_all_gear_recovered(player),
            None,
            "exploration"
        )
