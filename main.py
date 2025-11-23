from __future__ import annotations

import os
import sys

from systems import GameSystem

try:
    from llm_storyteller import LLMStoryTeller
except ImportError:
    print("Error: 'openai' package not installed.")
    print("Install with: pip install openai")
    sys.exit(1)


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Get a free API key at https://platform.openai.com")
        sys.exit(1)

    storyteller = LLMStoryTeller(api_key=api_key, model="gpt-4o-mini")
    game = GameSystem(storyteller)
    game.start_game()


if __name__ == "__main__":
    main()


