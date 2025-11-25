from __future__ import annotations

import time
from typing import List, Optional

import config
from rich.console import Console, Group
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Global Rich console instance
console = Console()


def clear_terminal() -> None:
    """Clear the terminal screen using ANSI escape codes (cross-platform)."""
    print("\033[2J\033[H", end="", flush=True)


def typewriter_print(text: str) -> None:
    """Print text with a typewriter effect (character by character).

    Args:
        text: The text to print
    """
    for char in text:
        print(char, end="", flush=True)
        if char != " ":  # Faster for spaces
            time.sleep(config.TYPEWRITER_DELAY)
    print()  # Newline at the end


def display_narrative_panel(text: str, mode: str = "exploration") -> None:
    """Display narrative text in a Rich panel with mode-appropriate styling.

    Args:
        text: The narrative text to display
        mode: Either "exploration" or "combat" for styling
    """
    # Choose border color and title based on mode
    if mode == "combat":
        border_style = "yellow"
        title = "⚔ COMBAT! ⚔"
    else:
        border_style = "white"
        title = "EXPLORATION"

    # For now, we'll use typewriter effect outside the panel, then show the panel
    # This is a compromise until we find a better UI solution
    typewriter_print(text)

    # Create and display the panel with the full text
    panel = Panel(text, title=title, border_style=border_style, padding=(1, 2))
    console.print(panel)


def show_mode_header(mode: str = "exploration") -> None:
    """Show padding before narrative (no longer shows rule - title is on panel now).

    Args:
        mode: Either "exploration" or "combat" (default: "exploration")
    """
    # Add some padding before the narrative panel
    console.print()


def render_status(player, mode: str = "exploration", enemy: Optional = None) -> None:
    """Render the status display using Rich library with different modes.

    Args:
        player: Player instance to display status for
        mode: Either "exploration" or "combat" (default: "exploration")
        enemy: Current Monster when in combat, otherwise None
    """
    if mode == "combat":
        # Combat mode: focused battle status
        _render_combat_status(player, enemy)
    else:
        # Exploration mode: full status with equipment
        _render_exploration_status(player)


def _render_exploration_status(player) -> None:
    """Render the full exploration status with stats, consumables, and equipment."""
    from models import DropResult

    # Calculate HP percentage and determine color
    hp_percentage = (player.health / player.max_health) * 100 if player.max_health > 0 else 0
    current_hp_str = str(player.health)

    # Create HP text with color based on percentage
    hp_text = Text()
    hp_text.append("HP:  ")
    if hp_percentage >= 75:
        hp_text.append(current_hp_str, style="bold green")
    elif hp_percentage >= 50:
        hp_text.append(current_hp_str, style="bold yellow")
    else:
        hp_text.append(current_hp_str, style="bold red")
    hp_text.append(f"/{player.max_health}")

    # Build left panel (Stats)
    stats_table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
    stats_table.add_row(hp_text)
    stats_table.add_row(f"Defense: {player.get_defense()}")

    consumables_table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
    consumables_table.add_row(f"Potions: {player.inventory.num_potions}")
    consumables_table.add_row(f"Scrolls: {player.inventory.num_escape_scrolls}")

    left_content = Group(
        Text("Stats", style="bold"),
        stats_table,
        Text(""),  # Blank line
        Text("Consumables", style="bold"),
        consumables_table,
    )

    # Build right panel (Equipment)
    equipment_map = [
        ("Helm", DropResult.HELM),
        ("Shoulders", DropResult.PAULDRONS),
        ("Chest", DropResult.CUIRASS),
        ("Legs", DropResult.LEG_GUARDS),
        ("Boots", DropResult.BOOTS),
        ("Sword", None),
        ("Shield", None),
    ]

    equipment_table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
    for display_name, drop_result in equipment_map:
        if drop_result is None:
            # Handle sword and shield separately
            if display_name == "Sword":
                has_item = player.has_sword
            else:  # Shield
                has_item = player.has_shield
        else:
            has_item = drop_result in player.owned_armor

        if has_item:
            status_text = Text("equipped", style="bold green")
        else:
            status_text = Text("—", style="dim")

        # Create row text: "Name: status"
        row_text = Text()
        row_text.append(f"{display_name}: ")
        row_text.append(status_text)
        equipment_table.add_row(row_text)

    right_content = Group(
        Text("Equipment", style="bold"),
        equipment_table,
    )

    # Create two-column layout
    columns = Columns([left_content, right_content], equal=True, expand=True)

    # Create panel with STATUS title
    panel = Panel(columns, title="STATUS", border_style="dim")

    # Print directly using Rich console
    console.print(panel)


def _render_combat_status(player, enemy) -> None:
    """Render the focused combat status with HP, Defense, and Enemy info."""
    # Calculate HP percentage and determine color
    hp_percentage = (player.health / player.max_health) * 100 if player.max_health > 0 else 0
    current_hp_str = str(player.health)

    # Create HP text with color based on percentage
    hp_text = Text()
    hp_text.append("HP:      ")
    if hp_percentage >= 75:
        hp_text.append(current_hp_str, style="bold green")
    elif hp_percentage >= 50:
        hp_text.append(current_hp_str, style="bold yellow")
    else:
        hp_text.append(current_hp_str, style="bold red")
    hp_text.append(f"/{player.max_health}")

    # Create combat status table
    battle_table = Table(show_header=False, show_edge=False, box=None, padding=(0, 1))
    battle_table.add_row("")  # Empty line at top
    battle_table.add_row(hp_text)
    battle_table.add_row(f"Defense: {player.get_defense()}")
    battle_table.add_row("")  # Empty line

    # Add enemy info if available
    if enemy:
        battle_table.add_row(f"Enemy:   {enemy.name}")
    else:
        battle_table.add_row("Enemy:   Unknown")

    battle_table.add_row("")  # Empty line at bottom

    # Create panel with BATTLE STATUS title
    panel = Panel(battle_table, title="BATTLE STATUS")

    # Print directly using Rich console
    console.print(panel)


def prompt_choice(title: str, options: List[str]) -> int:
    """Prompt user to choose from numbered options; returns zero-based index."""
    import sys

    lines = [title] + [f"{idx + 1}) {opt}" for idx, opt in enumerate(options)]
    print("\n".join(lines), flush=True)
    while True:
        sys.stdout.write("> ")
        sys.stdout.flush()
        try:
            # Try reading from stdin directly as a workaround for Git Bash issues
            user_input = sys.stdin.readline()
            if not user_input:
                raise EOFError("End of input")
            user_input = user_input.strip()
        except (EOFError, KeyboardInterrupt) as e:
            raise
        except Exception as e:
            print(f"Error reading input: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise
        if user_input.lower() == "x":
            print("Story Teller bows and ends the game...", flush=True)
            import sys
            sys.exit(0)
        if user_input.isdigit():
            choice_number = int(user_input)
            if 1 <= choice_number <= len(options):
                selected_index = choice_number - 1
                return selected_index
        print("Invalid input. Please enter a valid number.", flush=True)
