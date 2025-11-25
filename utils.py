"""Shared utilities and abstractions for the dungeon crawler game.

This module contains pure utility functions and shared abstractions that
are used across multiple modules in the game.
"""

from __future__ import annotations

import random
from typing import List, Protocol, Any

from models import WeightedOption


class RandomProvider(Protocol):
    """Protocol for random number generation (for testability).

    OO rationale: Small RNG abstraction to make probabilistic systems
    deterministic in tests and swappable in production.
    """
    def random(self) -> float: ...
    def randint(self, a: int, b: int) -> int: ...
    def choice(self, seq: List[Any]) -> Any: ...


class DefaultRandomProvider:
    """Default implementation bridging to Python's random module.

    OO rationale: Default implementation bridging to Python's random module.
    """
    def random(self) -> float:
        return random.random()

    def randint(self, a: int, b: int) -> int:
        return random.randint(a, b)

    def choice(self, seq: List[Any]) -> Any:
        return random.choice(seq)


def select_weighted_random(options: List[WeightedOption], random_provider: RandomProvider) -> str:
    """Select a random option from weighted choices using probability distribution.

    This function implements weighted random selection, where each option has a
    probability of being selected proportional to its weight. Higher weights
    mean higher probability of selection.

    Algorithm:
    1. Calculate total weight of all options
    2. Generate a random number between 0 and total_weight
    3. Iterate through options, accumulating weights until the random number
       falls within an option's range
    4. Return the label of the selected option

    Example:
        options = [
            WeightedOption("common", 10.0),   # 10/15 = 66.7% chance
            WeightedOption("rare", 4.0),      # 4/15 = 26.7% chance
            WeightedOption("epic", 1.0)       # 1/15 = 6.7% chance
        ]
        # Total weight = 15.0
        # Random number between 0-15 determines which option is selected

    Args:
        options: List of WeightedOption instances. Weight must be >= 0.
        random_provider: Random number generator (for testability).

    Returns:
        The label string of the selected option. If total_weight <= 0, returns
        the last option's label as a fallback.

    OO rationale: Centralized, pure utility that implements weighted selection.
    - Single-responsibility: callers (loot, rooms) don't duplicate probability logic.
    - Dependency inversion: consumes RandomProvider to remain deterministic in tests.
    - Decoupling: returns a label, letting each subsystem map labels to domain types.
    """
    if not options:
        raise ValueError("Cannot select from empty options list")

    total_weight = sum(option.weight for option in options)
    if total_weight <= 0:
        # Fallback: if all weights are zero/negative, return the last option as default
        default_option = options[-1]
        return default_option.label

    # Generate random number in range [0, total_weight)
    random_value = random_provider.random() * total_weight

    # Walk through options, accumulating weights until random_value falls within an option's range
    cumulative_weight = 0.0
    for option in options:
        cumulative_weight += option.weight
        if random_value <= cumulative_weight:
            return option.label

    # Fallback (shouldn't normally reach here due to floating point precision)
    # If we somehow didn't select anything, return the last option as default
    fallback_option = options[-1]
    return fallback_option.label
