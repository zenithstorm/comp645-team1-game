from __future__ import annotations

import time
from typing import List, Optional

import config
from rich.console import Console, Group
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Global Rich console instance with proper encoding for Windows
console = Console(force_terminal=True, legacy_windows=False)


def clear_terminal() -> None:
    """Clear the terminal screen using ANSI escape codes (cross-platform)."""
    print("\033[2J\033[H", end="", flush=True)


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

    # Create and display the panel directly (no typewriter effect)
    panel = Panel(text, title=title, border_style=border_style, padding=(1, 2))
    console.print()  # Add some spacing
    console.print(panel)


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

    # Left column: Stats and Consumables
    stats_table = Table.grid(padding=(0, 2))
    stats_table.add_column(justify="left")
    stats_table.add_column(justify="left")

    stats_table.add_row(hp_text, "")
    stats_table.add_row("Defense:", str(player.get_defense()))
    stats_table.add_row("")  # Spacing
    stats_table.add_row("[bold]Consumables[/]", "")
    stats_table.add_row("Potions:", str(player.inventory.num_potions))
    stats_table.add_row("Scrolls:", str(player.inventory.num_escape_scrolls))

    # Right column: Equipment
    equipment_table = Table.grid(padding=(0, 2))
    equipment_table.add_column(justify="left")
    equipment_table.add_column(justify="left")

    equipment_table.add_row("[bold]Equipment[/]", "")

    # Check individual armor pieces
    has_helm = DropResult.HELM in player.owned_armor
    has_pauldrons = DropResult.PAULDRONS in player.owned_armor
    has_cuirass = DropResult.CUIRASS in player.owned_armor
    has_gauntlets = DropResult.GAUNTLETS in player.owned_armor

    equipment_items = [
        ("Helm:", has_helm),
        ("Pauldrons:", has_pauldrons),
        ("Cuirass:", has_cuirass),
        ("Gauntlets:", has_gauntlets),
        ("Sword:", player.has_sword),
        ("Shield:", player.has_shield),
    ]

    for item_name, has_item in equipment_items:
        if has_item:
            equipment_table.add_row(item_name, "[bold green]equipped[/]")
        else:
            equipment_table.add_row(item_name, "[dim]—[/]")

    # Combine in columns
    content = Columns([stats_table, equipment_table], equal=True, expand=True)
    panel = Panel(content, title="STATUS")
    console.print(panel)


def _render_combat_status(player, enemy) -> None:
    """Render the focused combat status for battle."""
    # Calculate HP percentage and determine color
    hp_percentage = (player.health / player.max_health) * 100 if player.max_health > 0 else 0

    # Create HP text with color based on percentage
    hp_text = Text()
    hp_text.append("HP:  ")
    if hp_percentage >= 75:
        hp_text.append(str(player.health), style="bold green")
    elif hp_percentage >= 50:
        hp_text.append(str(player.health), style="bold yellow")
    else:
        hp_text.append(str(player.health), style="bold red")
    hp_text.append(f"/{player.max_health}")

    # Combat status table
    combat_table = Table.grid(padding=(0, 1))
    combat_table.add_column(justify="left")
    combat_table.add_column(justify="left")

    combat_table.add_row(hp_text, "")
    combat_table.add_row("Defense:", str(player.get_defense()))
    combat_table.add_row("")  # Spacing
    if enemy:
        combat_table.add_row("Enemy:", enemy.name)

    panel = Panel(combat_table, title="BATTLE STATUS")
    console.print(panel)


def prompt_choice(title: str, options: List[str]) -> int:
    """Prompt the user to choose from a list of options.

    Args:
        title: The prompt title to display
        options: List of option strings to choose from

    Returns:
        The index of the selected option (0-based)
    """
    # Display the title and options
    console.print(f"\n[bold]{title}[/]")
    for idx, option in enumerate(options):
        console.print(f"{idx + 1}) {option}")

    # Get user input
    while True:
        try:
            user_input = input("> ").strip()

            # Handle exit command
            if user_input.lower() == "x":
                console.print("Goodbye!")
                exit(0)

            # Handle numeric choice
            if user_input.isdigit():
                choice_number = int(user_input)
                if 1 <= choice_number <= len(options):
                    return choice_number - 1

            console.print("[red]Invalid input. Please enter a valid number or 'x' to exit.[/]")
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!")
            exit(0)
