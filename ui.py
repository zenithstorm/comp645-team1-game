from __future__ import annotations

from typing import List


def show(storyteller, context_text: str) -> None:
    """Display text via storyteller decoration."""
    # Strip prefixes like "encounter:", "game:start:", "status:", "loot:", "room:" before displaying
    # These prefixes are used internally for LLM tracking but shouldn't be shown to users
    text = storyteller.get_current_description(context_text)
    # Remove common prefixes (format: "prefix: rest of text")
    prefixes = ["encounter:", "game:start:", "game:victory:", "game:over:", "status:", "loot:", "room:", "rest:", "potion:", "attack:", "retaliation:", "flee:", "victory:"]
    for prefix in prefixes:
        if text.startswith(prefix):
            # Remove prefix and any following whitespace
            text = text[len(prefix):].lstrip()
            break
    print(text, flush=True)


def prompt_choice(storyteller, title: str, options: List[str]) -> int:
    """Prompt user to choose from numbered options; returns zero-based index."""
    import sys

    lines = [title] + [f"{idx + 1}) {opt}" for idx, opt in enumerate(options)]
    show(storyteller, "\n".join(lines))
    while True:
        sys.stdout.write("> ")
        sys.stdout.flush()
        try:
            # Try reading from stdin directly as a workaround for Git Bash issues
            raw_input_value = sys.stdin.readline()
            if not raw_input_value:
                raise EOFError("End of input")
            raw_input_value = raw_input_value.strip()
        except (EOFError, KeyboardInterrupt) as e:
            raise
        except Exception as e:
            print(f"Error reading input: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise
        if raw_input_value.isdigit():
            selection_number = int(raw_input_value)
            if 1 <= selection_number <= len(options):
                selected_idx = selection_number - 1
                return selected_idx
        show(storyteller, "Invalid input. Please enter a valid number.")
