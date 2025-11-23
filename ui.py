from __future__ import annotations

from typing import List


def show(storyteller, context_text: str) -> None:
    """Display text via storyteller decoration."""
    print(storyteller.get_current_description(context_text))


def prompt_choice(storyteller, title: str, options: List[str]) -> int:
    """Prompt user to choose from numbered options; returns zero-based index."""
    lines = [title] + [f"{idx + 1}) {opt}" for idx, opt in enumerate(options)]
    show(storyteller, "\n".join(lines))
    while True:
        raw_input_value = input("> ").strip()
        if raw_input_value.isdigit():
            selection_number = int(raw_input_value)
            if 1 <= selection_number <= len(options):
                return selection_number - 1
        show(storyteller, "Invalid input. Please enter a valid number.")


