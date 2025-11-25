from __future__ import annotations

from typing import List


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
