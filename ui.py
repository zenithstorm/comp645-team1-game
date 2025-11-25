from __future__ import annotations

import shutil
import time
from typing import List, Optional

import config


def clear_terminal() -> None:
    """Clear the terminal screen using ANSI escape codes (cross-platform)."""
    print("\033[2J\033[H", end="", flush=True)


def red(text: str) -> str:
    """Wrap text with red ANSI color codes.

    Can be combined with other formatting functions (e.g., bold(red("text"))).

    Args:
        text: The text to color red

    Returns:
        Text wrapped with red ANSI codes
    """
    # Remove any existing reset codes from nested formatting, then wrap
    text_without_reset = text.replace("\033[0m", "")
    return f"\033[31m{text_without_reset}\033[0m"


def green(text: str) -> str:
    """Wrap text with green ANSI color codes.

    Can be combined with other formatting functions (e.g., bold(green("text"))).

    Args:
        text: The text to color green

    Returns:
        Text wrapped with green ANSI codes
    """
    # Remove any existing reset codes from nested formatting, then wrap
    text_without_reset = text.replace("\033[0m", "")
    return f"\033[32m{text_without_reset}\033[0m"


def yellow(text: str) -> str:
    """Wrap text with yellow ANSI color codes.

    Can be combined with other formatting functions (e.g., bold(yellow("text"))).

    Args:
        text: The text to color yellow

    Returns:
        Text wrapped with yellow ANSI codes
    """
    # Remove any existing reset codes from nested formatting, then wrap
    text_without_reset = text.replace("\033[0m", "")
    return f"\033[33m{text_without_reset}\033[0m"


def orange(text: str) -> str:
    """Wrap text with orange ANSI color codes (using 256-color mode).

    Can be combined with other formatting functions (e.g., bold(orange("text"))).

    Args:
        text: The text to color orange

    Returns:
        Text wrapped with orange ANSI codes
    """
    # Remove any existing reset codes from nested formatting, then wrap
    # Using 256-color mode for orange (color 208)
    text_without_reset = text.replace("\033[0m", "")
    return f"\033[38;5;208m{text_without_reset}\033[0m"


def bold(text: str) -> str:
    """Wrap text with bold ANSI formatting codes.

    Can be combined with other formatting functions (e.g., green(bold("text"))).

    Args:
        text: The text to make bold

    Returns:
        Text wrapped with bold ANSI codes
    """
    # Remove any existing reset codes from nested formatting, then wrap
    text_without_reset = text.replace("\033[0m", "")
    return f"\033[1m{text_without_reset}\033[0m"


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


def create_equipment_display(player) -> str:
    """Create a formatted equipment display showing what gear the player has.

    Args:
        player: Player instance to check equipment status

    Returns:
        Multi-line string showing equipment status with green bold "equipped" text
    """
    from models import DropResult

    # Map DropResult to display names
    equipment_map = [
        ("Helm", DropResult.HELM),
        ("Shoulders", DropResult.PAULDRONS),
        ("Chest", DropResult.CUIRASS),
        ("Legs", DropResult.LEG_GUARDS),
        ("Boots", DropResult.BOOTS),
        ("Sword", None),  # Special case - uses has_sword
        ("Shield", None),  # Special case - uses has_shield
    ]

    lines = [bold("Equipment")]
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
            # Combine green and bold: can be nested in either order
            status = bold(green("equipped"))
        else:
            status = "none"

        lines.append(f"{display_name}: {status}")

    return "\n".join(lines)


def create_status_display(player) -> str:
    """Create a formatted status display with visual separators.

    Args:
        player: Player instance to display status for

    Returns:
        Formatted status display string
    """
    try:
        terminal_width = shutil.get_terminal_size().columns
    except (OSError, AttributeError):
        terminal_width = 80

    # Calculate HP percentage and apply color coding to current HP: green >= 75%, yellow >= 50%, red < 50%
    hp_percentage = (player.health / player.max_health) * 100 if player.max_health > 0 else 0

    current_hp_str = str(player.health)
    if hp_percentage >= 75:
        current_hp_colored = bold(green(current_hp_str))
    elif hp_percentage >= 50:
        current_hp_colored = bold(yellow(current_hp_str))
    else:
        current_hp_colored = bold(red(current_hp_str))

    hp = f"HP {current_hp_colored}/{player.max_health}"

    defense = f"Defense {player.get_defense()}"
    pots = f"Potions {player.inventory.num_potions}"
    scrolls = f"Escape Scrolls {player.inventory.num_escape_scrolls}"
    abilities = ["Holy Smite"]
    if player.has_shield:
        abilities.append("Shield Bash")
    if player.has_sword:
        abilities.append("Sword Slash")
    abilities_str = "Abilities: " + ", ".join(abilities)

    # Create equipment display
    equipment_display = create_equipment_display(player)

    # Create a visually distinct status box
    separator = "═" * terminal_width
    status_line = f"{hp} | {defense} | {pots} | {scrolls}"
    # Subtle exit hint in the footer
    exit_hint = "  (Press 'x' to exit)"
    return f"\n{separator}\n📜 STATUS\n{separator}\n{status_line}\n{abilities_str}\n{separator}\n{equipment_display}\n{separator}{exit_hint}\n"


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
            print("Exiting game...", flush=True)
            import sys
            sys.exit(0)
        if user_input.isdigit():
            choice_number = int(user_input)
            if 1 <= choice_number <= len(options):
                selected_index = choice_number - 1
                return selected_index
        print("Invalid input. Please enter a valid number.", flush=True)
