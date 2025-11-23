from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


def show(storyteller, context_text: str) -> None:
    """Display text via storyteller decoration."""
    print(storyteller.get_current_description(context_text))

@dataclass
class NarrativeEvent:
    # OO rationale: Lightweight value object representing a structured
    # narrative signal. Keeps the UI-to-StoryTeller boundary typed while
    # still serializing to the current string-based storyteller interface.
    kind: str
    payload: Dict[str, Any]

def show_event(storyteller, event: NarrativeEvent) -> None:
    """Serialize a NarrativeEvent to the storyteller context format."""
    # Simple, readable serialization: "kind: key=value; key=value"
    key_value_pairs = [f"{key}={value}" for key, value in event.payload.items()]
    text = f"{event.kind}: " + "; ".join(key_value_pairs)
    show(storyteller, text)


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


