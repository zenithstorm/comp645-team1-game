"""Monster generation system for the dungeon crawler game.

This module handles all monster creation logic, including regular monsters
and boss encounters based on game progress.
"""

from __future__ import annotations

from typing import List, Protocol, Any

import config
from models import Monster, MonsterTemplate, Weakness


class RandomProvider(Protocol):
    """Protocol for random number generation (for testability)."""
    def random(self) -> float: ...
    def randint(self, a: int, b: int) -> int: ...
    def choice(self, seq: List[Any]) -> Any: ...


class MonsterGenerator:
    """Generates monsters based on templates and game progress.

    OO rationale: Factory responsible for building fully-formed Monster
    instances from templates. Centralizes variability (names, stats,
    weaknesses) and keeps creation logic out of the game loop.
    Handles both regular monsters and boss spawning logic.
    """

    def __init__(self, random_provider: RandomProvider) -> None:
        self.random_provider = random_provider
        self._templates = [
            # Regular foes
            MonsterTemplate(
                name="Skeleton",
                weaknesses=[Weakness.HOLY_SMITE],
                description="A humanoid frame of loose bones held by brittle bindings; light, rattling steps and hollow gaze.",
            ),
            MonsterTemplate(
                name="Goblin Bandit",
                weaknesses=[Weakness.SWORD_SLASH],
                description="A small, agile greenskin with oversized ears and quick hands; favors scavenged gear and sudden lunges.",
            ),
            MonsterTemplate(
                name="Giant Rat",
                weaknesses=[Weakness.SHIELD_BASH],
                description="An oversized rat with patchy fur and prominent incisors; jittery, low to the ground, always testing distance.",
            ),
            MonsterTemplate(
                name="Wraith",
                weaknesses=[Weakness.HOLY_SMITE],
                description="A dim, humanoid outline woven from chill mist; light fades and warmth thins in its presence.",
            ),
        ]

    def generate_monster(self, monsters_defeated: int) -> Monster:
        """Generate a monster based on current game progress.

        Args:
            monsters_defeated: Number of monsters defeated so far

        Returns:
            Monster instance (regular monster or boss based on game progress)
        """
        # Check if boss should spawn based on progress
        if (monsters_defeated >= config.BOSS_SPAWN_THRESHOLD and
            self.random_provider.random() < config.BOSS_SPAWN_CHANCE):
            return self._create_boss()
        else:
            return self._create_regular_monster()

    def _create_regular_monster(self) -> Monster:
        """Create a regular monster from templates."""
        monster_template = self.random_provider.choice(self._templates)
        max_health_points = monster_template.hp or self.random_provider.randint(
            config.MONSTER_HEALTH_MIN, config.MONSTER_HEALTH_MAX
        )
        attack_strength = monster_template.strength or self.random_provider.randint(
            config.MONSTER_STRENGTH_MIN, config.MONSTER_STRENGTH_MAX
        )
        return Monster(
            max_health=max_health_points,
            strength=attack_strength,
            name=monster_template.name,
            weaknesses=list(monster_template.weaknesses),
            description=monster_template.description,
            is_boss=monster_template.is_boss,
        )

    def _create_boss(self) -> Monster:
        """Create the end-game boss monster."""
        # Single end-of-run boss
        boss_template = MonsterTemplate(
            name="Grave Tyrant",
            weaknesses=[],
            description=(
                "An armored lich-king draped in funereal banners. A corroded crown sits on a skull carved with runes; "
                "a great blade of black iron rests across its lap. Plates of ornate mail are missing in places, "
                "revealing ribs choked with grave dust. Clutched in its skeletal grasp, the Heart of Radiance pulses "
                "with a faint, struggling light—the sacred relic you came to reclaim, its divine radiance dimmed but "
                "not extinguished by the creature's dark presence."
            ),
            hp=config.BOSS_HP,
            strength=config.BOSS_STRENGTH,
            is_boss=True,
        )
        # Use the template values directly (no randomization for boss)
        return Monster(
            max_health=boss_template.hp,
            strength=boss_template.strength,
            name=boss_template.name,
            weaknesses=list(boss_template.weaknesses),
            description=boss_template.description,
            is_boss=boss_template.is_boss,
        )
