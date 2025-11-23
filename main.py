from __future__ import annotations

from .systems import GameSystem


def main() -> None:
    game = GameSystem()
    game.start_game()


if __name__ == "__main__":
    main()


