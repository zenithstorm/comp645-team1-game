from __future__ import annotations

from typing import List


def show(storyteller, text: str) -> None:
    """Display text to the user."""
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
        if user_input.isdigit():
            choice_number = int(user_input)
            if 1 <= choice_number <= len(options):
                selected_index = choice_number - 1
                return selected_index
        show(storyteller, "Invalid input. Please enter a valid number.")
