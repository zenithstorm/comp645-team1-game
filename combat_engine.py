"""Combat system engine for the dungeon crawler game.

This module handles all combat-related logic including action availability,
damage calculations, combat flow, and monster defeat handling.
"""

from __future__ import annotations

from typing import List, Optional

import config
import ui
from models import Action, Monster, Player, Weakness
from narrative_engine import NarrativeEngine


class CombatEngine:
    """Handles all combat mechanics and calculations.

    OO rationale: Separates combat concerns from game orchestration. This class
    encapsulates combat rules, damage calculations, action availability, and
    combat flow logic, making it easier to test and modify combat mechanics.
    """

    # Action to weakness mapping (used for combat calculations)
    ACTION_TO_WEAKNESS = {
        Action.HOLY_SMITE: Weakness.HOLY_SMITE,
        Action.SWORD_SLASH: Weakness.SWORD_SLASH,
        Action.SHIELD_BASH: Weakness.SHIELD_BASH,
    }

    def __init__(self, narrative_engine: NarrativeEngine, random_provider) -> None:
        """Initialize the combat engine.

        Args:
            narrative_engine: The narrative engine for combat descriptions
            random_provider: Random number generator for combat calculations
        """
        self.narrative_engine = narrative_engine
        self.random_provider = random_provider

    def get_available_actions(self, player: Player) -> List[Action]:
        """Get list of available combat actions for the player.

        Args:
            player: The player to check available actions for

        Returns:
            List of available Action enums
        """
        options: List[Action] = list(player.abilities().keys())
        # Only show potion option if player is injured AND has potions
        if player.health < player.max_health and player.inventory.num_potions > 0:
            options.append(Action.USE_POTION)
        options.append(Action.FLEE)
        return options

    def get_action_label(self, action: Action) -> str:
        """Get display label for a combat action.

        Args:
            action: The action to get a label for

        Returns:
            Human-readable action label
        """
        action_labels = {
            Action.HOLY_SMITE: "Holy Smite",
            Action.SWORD_SLASH: "Sword Slash",
            Action.SHIELD_BASH: "Shield Bash",
            Action.USE_POTION: "Use Potion",
            Action.FLEE: "Flee",
        }
        return action_labels[action]

    def calculate_player_damage(self, action: Action, player: Player, monster: Monster) -> int:
        """Calculate damage dealt by player action against monster.

        Args:
            action: The action being performed
            player: The player performing the action
            monster: The target monster

        Returns:
            Final damage amount after weakness bonuses
        """
        ability_map = player.abilities()
        dmg_fn = ability_map.get(action)
        if dmg_fn is None:
            return 0
        base = dmg_fn()
        return monster.apply_weakness_bonus(action, base)

    def execute_combat_turn(self, player: Player, monster: Monster, selected_action: Action) -> dict:
        """Execute a complete combat turn and return results.

        Args:
            player: The player performing the action
            monster: The target monster
            selected_action: The action being performed

        Returns:
            Dictionary containing combat turn results:
            - action_executed: bool
            - player_damage_dealt: int
            - monster_died: bool
            - is_weakness_hit: bool
            - monster_retaliation_damage: Optional[int]
            - player_health_after: Optional[int]
        """
        # Handle non-damage actions first
        if selected_action == Action.USE_POTION:
            self.narrative_engine.describe_potion_use(player)
            return {"action_executed": True, "non_damage_action": True}

        elif selected_action == Action.FLEE:
            flee_succeeded = player.attempt_flee(self.random_provider.random)
            self.narrative_engine.describe_flee_attempt(flee_succeeded, monster.name)
            return {"action_executed": True, "flee_succeeded": flee_succeeded, "non_damage_action": True}

        # Handle combat actions (Holy Smite, Shield Bash, Sword Slash)
        ability_map = player.abilities()
        base_damage = ability_map[selected_action]()
        final_damage = self.calculate_player_damage(selected_action, player, monster)

        # Check if it's a weakness hit
        matching_weakness = self.ACTION_TO_WEAKNESS.get(selected_action)
        is_weakness = (matching_weakness is not None and
                      matching_weakness in monster.weaknesses and
                      final_damage > base_damage)

        # Apply player damage
        damage_dealt = monster.take_damage(final_damage)
        monster_died = not monster.is_alive()

        # Handle monster retaliation if it survived
        monster_retaliation_damage = None
        player_health_after = None
        if not monster_died:
            monster_attack_damage = monster.attack()
            monster_retaliation_damage = player.take_damage(monster_attack_damage, defense=player.get_defense())
            player_health_after = player.health

        return {
            "action_executed": True,
            "non_damage_action": False,
            "player_damage_dealt": damage_dealt,
            "monster_died": monster_died,
            "is_weakness_hit": is_weakness,
            "monster_retaliation_damage": monster_retaliation_damage,
            "player_health_after": player_health_after,
            "base_damage": base_damage,
            "final_damage": final_damage
        }

    def handle_monster_defeat(self, monster: Monster, player: Player,
                            final_action: Optional[Action] = None,
                            is_weakness: bool = False) -> bool:
        """Handle monster defeat: victory narration and determine if game should end.

        Args:
            monster: The defeated monster
            player: The player who defeated the monster
            final_action: The action that killed the monster
            is_weakness: Whether the final action was a weakness hit

        Returns:
            True if the game should end (boss defeated), False otherwise
        """
        item_name = self.narrative_engine.format_item_name(monster.item_drop)

        # If we know the final action, include it in the victory description
        action_label = self.get_action_label(final_action) if final_action else None

        self.narrative_engine.describe_victory(
            monster,
            item_name,
            player,
            final_action=action_label,
            is_weakness=is_weakness
        )

        # If boss is defeated, end the run with victory
        return monster.is_boss

    def run_combat_phase(self, player: Player, monster: Monster) -> tuple[Optional[Monster], Optional[Action], bool]:
        """Run the complete combat phase until resolution.

        Args:
            player: The player in combat
            monster: The monster being fought

        Returns:
            Tuple of (monster_if_defeated, final_action, is_weakness_hit) or (None, None, False) if fled
        """
        while player.is_alive() and monster.is_alive():
            available_actions = self.get_available_actions(player)
            action_labels = [self.get_action_label(action) for action in available_actions]
            selected_index = ui.prompt_choice("⚔️ In battle, choose your action:", action_labels)
            selected_action = available_actions[selected_index]

            # Execute the combat turn
            turn_result = self.execute_combat_turn(player, monster, selected_action)

            # Handle non-damage actions
            if turn_result.get("non_damage_action"):
                if turn_result.get("flee_succeeded"):
                    return None, None, False  # Combat ended - player fled
                continue  # Continue combat loop for potion use

            # Handle damage actions
            if turn_result["monster_died"]:
                # Monster died - return monster and combat details for defeat handling
                return monster, selected_action, turn_result["is_weakness_hit"]
            else:
                # Monster survived - describe the complete turn (player action + monster retaliation)
                self.narrative_engine.describe_combat_turn(
                    self.get_action_label(selected_action),
                    monster,
                    turn_result["player_damage_dealt"],
                    turn_result["is_weakness_hit"],
                    player,
                    monster_retaliation_damage=turn_result["monster_retaliation_damage"],
                    player_health_after=turn_result["player_health_after"]
                )

            # Update UI after each turn if player is still alive
            if player.is_alive():
                ui.render_status(player, mode="combat", enemy=monster)

        # Combat ended - return None to indicate completion
        return None, None, False
