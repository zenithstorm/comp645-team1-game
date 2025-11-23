#!/usr/bin/env python3
"""Run the game with AI-powered StoryTeller using OpenAI."""

import os
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from systems import GameSystem

def main():
    """Run the game with AI StoryTeller (required)."""
    try:
        from llm_storyteller import LLMStoryTeller
    except ImportError:
        print("Error: 'openai' package not installed.")
        print("Install with: pip install openai")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Get a free API key at https://platform.openai.com")
        print("Then set it with:")
        print("  Windows PowerShell: $env:OPENAI_API_KEY='your-key-here'")
        print("  Windows CMD: set OPENAI_API_KEY=your-key-here")
        print("  Linux/Mac: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)

    try:
        storyteller = LLMStoryTeller(api_key=api_key, model="gpt-4o-mini")
        game = GameSystem(storyteller)
        game.start_game()
    except Exception as e:
        print(f"Error setting up AI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
