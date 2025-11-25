"""Loot and item drop system for the dungeon crawler game.

This module handles all item generation logic, including drop calculations,
loot buckets, and unique item tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import config
from models import DropResult, Player, WeightedOption
from utils import RandomProvider, select_weighted_random

@dataclass
class LootBucket:
    """Represents a loot category with its drop probability."""
    category: str  # Will map to DropResult enum values
    weight: float

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise ValueError(f"Weight must be non-negative, got {self.weight}")

    @classmethod
    def create_buckets(cls, player: 'Player', remaining_armor: List['DropResult']) -> List['LootBucket']:
        """Factory method to create all loot buckets with proper weights."""
        # Build base weights from config
        weight_no_item = config.DROP_WEIGHTS["NO_ITEM"]
        weight_health_potion = config.DROP_WEIGHTS["HEALTH_POTION"]
        weight_escape_scroll = config.DROP_WEIGHTS["ESCAPE_SCROLL"]
        weight_armor = config.DROP_WEIGHTS["ARMOR"] if remaining_armor else 0.0

        # If no armor remains, redistribute armor weight to 'no item'
        if not remaining_armor:
            weight_no_item += config.DROP_WEIGHTS["ARMOR"]

        return [
            cls("NO_ITEM", weight_no_item),
            cls("HEALTH_POTION", weight_health_potion),
            cls("ESCAPE_SCROLL", weight_escape_scroll),
            cls("ARMOR", weight_armor),
        ]


class DropCalculator:
    """Handles loot generation with unique armor pieces and scripted gear recovery.

    OO rationale: Encapsulates loot rules and unique item availability.
    This isolates drop probability and uniqueness constraints from combat
    flow, making it easy to tune or swap strategies.
    """

    def __init__(self, random_provider: RandomProvider) -> None:
        self.random_provider = random_provider
        # Track all unique gear that can still drop (shield, sword, and armor pieces)
        self._remaining_gear: List[DropResult] = list(DropResult.unique_gear())

    def get_drop_for_monster(self, defeated_count: int, player: Player) -> DropResult:
        """Get the drop for a monster encounter (guaranteed progression items or random drop).

        Checks for guaranteed progression items (shield/sword) first, then falls back
        to a random drop if no guaranteed item is due.

        Args:
            defeated_count: Number of monsters defeated so far
            player: Player instance to check current equipment

        Returns:
            DropResult for the item that will drop
        """
        # Check for guaranteed progression items first
        # Shield guaranteed on 1st monster (defeated_count will be 1 after this fight)
        if defeated_count == 0 and not player.has_shield and DropResult.SHIELD in self._remaining_gear:
            self._remaining_gear.remove(DropResult.SHIELD)
            return DropResult.SHIELD
        # Sword guaranteed on 3rd monster (defeated_count will be 3 after this fight)
        if defeated_count == 2 and not player.has_sword and DropResult.SWORD in self._remaining_gear:
            self._remaining_gear.remove(DropResult.SWORD)
            return DropResult.SWORD
        # Otherwise, roll for a random drop (but exclude shield/sword if already dropped)
        return self.roll_item_drop(player)

    def roll_item_drop(self, player: Player) -> DropResult:
        """Roll for a random item drop, excluding unique items that have already been dropped.

        Args:
            player: Player instance to check current equipment (for defensive checks)
        """
        # Check if any gear (armor pieces) remain
        # Filter _remaining_gear to get only armor pieces (exclude shield and sword)
        remaining_armor = [item for item in self._remaining_gear if item not in (DropResult.SHIELD, DropResult.SWORD)]

        # Create loot buckets using the factory method
        loot_buckets = LootBucket.create_buckets(player, remaining_armor)

        # Convert to WeightedOption for selection
        weighted_options = [WeightedOption(bucket.category, bucket.weight) for bucket in loot_buckets]
        chosen_bucket = select_weighted_random(weighted_options, self.random_provider)

        # Map bucket names to DropResult values
        bucket_to_drop = {
            "NO_ITEM": DropResult.NO_ITEM,
            "HEALTH_POTION": DropResult.HEALTH_POTION,
            "ESCAPE_SCROLL": DropResult.ESCAPE_SCROLL,
        }

        if chosen_bucket in bucket_to_drop:
            return bucket_to_drop[chosen_bucket]

        if chosen_bucket == "ARMOR" and remaining_armor:
            armor_piece = self.random_provider.choice(remaining_armor)
            self._remaining_gear.remove(armor_piece)
            return armor_piece
        return DropResult.NO_ITEM
