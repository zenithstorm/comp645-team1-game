"""LLM-powered StoryTeller using OpenAI.

New OpenAI accounts get free credits ($5-18), and gpt-4o-mini is very affordable
(~$0.15 per 1M tokens), so you can play many games for free!
"""

from __future__ import annotations

from typing import Union, List, Optional

# Handle both package and direct imports
try:
    from .models import DropResult
except ImportError:
    from models import DropResult


class LLMStoryTeller:
    """StoryTeller using OpenAI's API to generate creative item descriptions.

    Maintains conversation history across the game session so the LLM remembers
    what has happened previously.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o-mini"):
        """Initialize with OpenAI API key.

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            model: Model to use. Default "gpt-4o-mini" is cheap and fast.
                    Other options: "gpt-4" (better quality), "gpt-3.5-turbo" (faster)
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. Install with: pip install openai"
            )

        self.client = OpenAI(api_key=api_key)
        self.model = model
        # Maintain conversation history for the game session
        self.conversation_history: List[dict] = [
            {
                "role": "system",
                "content": "You are a creative writer for a dark fantasy dungeon crawler game. The player is a holy knight/paladin whose gear was stolen by goblin bandits. The items found are the player's own stolen equipment, which was taken from them during an ambush."
            }
        ]

    def _check_quota_error(self, e: Exception) -> None:
        """Check if an exception is a quota/rate limit error and exit if so.

        Args:
            e: The exception to check
        """
        error_str = str(e).lower()
        error_type = type(e).__name__
        if ("insufficient_quota" in error_str or
            (error_type == "RateLimitError" and "quota" in error_str) or
            ("429" in error_str and "quota" in error_str)):
            print("\n" + "="*60)
            print("Error: OpenAI API quota exceeded.")
            print("="*60)
            print("Your OpenAI account has run out of credits.")
            print("Please check your account billing and add credits:")
            print("  https://platform.openai.com/account/billing")
            print("="*60)
            import sys
            sys.exit(1)

    def _call_llm(self, messages: List[dict], max_tokens: int, temperature: float = 0.8) -> str:
        """Make an LLM API call and return the response content.

        Args:
            messages: List of message dicts for the API call
            max_tokens: Maximum tokens for the response
            temperature: Temperature for the API call (default 0.8)

        Returns:
            The response content as a string

        Raises:
            Exception: Re-raises any non-quota errors
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            # Check if response was truncated due to token limit
            finish_reason = response.choices[0].finish_reason
            if finish_reason == "length":
                print(f"[WARNING] Response truncated due to token limit (finish_reason: {finish_reason})", flush=True)
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned None content")
            return content.strip()
        except Exception as e:
            # Print error for debugging
            print(f"\n[ERROR] LLM API call failed: {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self._check_quota_error(e)
            # Re-raise other errors
            raise

    def add_game_event(self, event_text: str) -> None:
        """Add a game event to the conversation history so the LLM remembers it.

        Args:
            event_text: Description of what happened in the game (e.g., "encounter: Enemy spotted: Skeleton")
        """
        # Extract meaningful events (skip status updates, etc.)
        if event_text.startswith(("encounter:", "victory:", "loot:", "game:")):
            self.conversation_history.append({
                "role": "assistant",
                "content": event_text
            })

    def get_current_description(self, context: str) -> str:
        """Format context text and optionally add to conversation history."""
        # Add significant events to history
        if context.startswith(("encounter:", "victory:", "loot:", "game:", "attack:", "retaliation:", "potion:", "flee:", "rest:")):
            self.add_game_event(context)
        return context.strip()

    def describe_player_action(
        self,
        action: str,
        monster_name: str,
        monster_description: str,
        damage: int,
        is_weakness: bool = False,
        has_shield: bool = False,
        has_sword: bool = False,
        has_armor: bool = False
    ) -> str:
        """Generate narrative description of a player's combat action.

        Args:
            action: The action name (e.g., "Holy Smite", "Shield Bash", "Sword Slash")
            monster_name: Name of the monster
            monster_description: Description of the monster
            damage: Damage dealt
            is_weakness: Whether this was a weakness hit
            has_shield: Whether the player has a shield
            has_sword: Whether the player has a sword
            has_armor: Whether the player has any armor pieces
        """
        player_context = self._get_player_context(has_shield, has_sword, has_armor)
        weakness_text = " The creature is particularly vulnerable to this attack!" if is_weakness else ""

        prompt = f"""A holy knight/paladin is in combat with:
- Monster: {monster_name}
- Description: {monster_description}

{player_context}

The player uses: {action}
Damage dealt: {damage}{weakness_text}

Write a vivid 2-3 sentence description of how this action unfolds. Describe the holy knight's movements, the divine power or weapon, and the impact on the monster. Be cinematic and immersive, like a dungeon master narrating combat.

IMPORTANT: Only mention equipment (shield, sword, armor) if the player actually has it. If they don't have armor, describe them in simple clothing/robes, not armor.

Examples:
- For Holy Smite (no equipment): "You raise your hand, calling upon the Light. Divine radiance blazes forth, striking the creature with searing holy energy. The monster recoils as the sacred power burns through its form."
- For Shield Bash (has shield): "You surge forward, your shield leading the charge. The heavy impact sends the creature staggering backward, its balance broken by the weight of your righteous defense."
- For Sword Slash (has sword): "Your blade arcs through the air, catching the torchlight. The steel finds its mark, cutting deep as you channel your strength into the strike."

Write only the description, no quotes or labels:"""

        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})

        description = self._call_llm(messages, max_tokens=250)
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Player action ({action}): {description}"
        })
        return description

    def describe_monster_attack(
        self,
        monster_name: str,
        monster_description: str,
        damage: int,
        player_health_after: int,
        has_shield: bool = False,
        has_sword: bool = False,
        has_armor: bool = False
    ) -> str:
        """Generate narrative description of a monster's attack.

        Args:
            monster_name: Name of the monster
            monster_description: Description of the monster
            damage: Damage dealt
            player_health_after: Player's health after the attack
            has_shield: Whether the player has a shield
            has_sword: Whether the player has a sword
            has_armor: Whether the player has any armor pieces
        """
        player_context = self._get_player_context(has_shield, has_sword, has_armor)
        prompt = f"""A holy knight/paladin is being attacked by:
- Monster: {monster_name}
- Description: {monster_description}
- Damage dealt: {damage}
- Player's remaining health: {player_health_after}

{player_context}

Write a vivid 2-3 sentence description of the monster's attack. Describe how the creature strikes, the knight's reaction, and the impact. Be cinematic and immersive, like a dungeon master narrating combat.

IMPORTANT: Only mention equipment (shield, sword, armor) if the player actually has it. If they don't have armor, describe them in simple clothing/robes, not armor. If they don't have a shield, they can't raise a shield to block.

Example style (no armor, no shield):
"The creature lunges forward with surprising speed, claws raking across your robes. You try to dodge, but the force of the blow still finds its way through, leaving you winded and bleeding."

Write only the description, no quotes or labels:"""

        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})

        description = self._call_llm(messages, max_tokens=250)
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Monster attack: {description}"
        })
        return description

    def describe_victory(
        self,
        monster_name: str,
        monster_description: str,
        items_acquired: List[str],
        has_shield: bool = False,
        has_sword: bool = False,
        has_armor: bool = False
    ) -> str:
        """Generate narrative description of defeating a monster.

        Args:
            monster_name: Name of the monster
            monster_description: Description of the monster
            items_acquired: List of items being acquired (e.g., ["a shield", "health potion"])
            has_shield: Whether the player already has a shield (before acquiring new items)
            has_sword: Whether the player already has a sword (before acquiring new items)
            has_armor: Whether the player already has any armor pieces (before acquiring new items)
        """
        player_context = self._get_player_context(has_shield, has_sword, has_armor)
        items_text = ""
        if items_acquired:
            if len(items_acquired) == 1:
                items_text = f" The creature had: {items_acquired[0]}"
            else:
                items_text = f" The creature had: {', '.join(items_acquired[:-1])}, and {items_acquired[-1]}"

        prompt = f"""A holy knight/paladin has just defeated:
- Monster: {monster_name}
- Description: {monster_description}
{items_text}

{player_context}

Write a vivid 2-3 sentence description of the monster's defeat. Describe how it falls, the final moments, and if items are present, how the knight retrieves them. Be cinematic and immersive, like a dungeon master narrating victory.

IMPORTANT: Only mention equipment (shield, sword, armor) if the player actually has it or is acquiring it. If they don't have armor, describe them in simple clothing/robes, not armor.

Example style:
"The skeleton's bones rattle one last time as your holy smite shatters its form. It collapses in a heap of scattered bones, the dark magic animating it finally extinguished. You notice your shield clutched in its bony grasp and carefully retrieve it, feeling the familiar weight return to your arm."

Write only the description, no quotes or labels:"""

        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})

        description = self._call_llm(messages, max_tokens=300)
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Victory over {monster_name}: {description}"
        })
        return description

    def _get_player_context(self, has_shield: bool = False, has_sword: bool = False, has_armor: bool = False) -> str:
        """Generate context string about the player's current equipment state."""
        equipment = []
        if not has_shield and not has_sword and not has_armor:
            return "IMPORTANT: The player has NO armor, NO shield, and NO sword. All their gear was stolen by goblin bandits. They are wearing only basic clothing/robes, not armor."
        if has_shield:
            equipment.append("shield")
        if has_sword:
            equipment.append("sword")
        if has_armor:
            equipment.append("armor")
        return f"The player currently has: {', '.join(equipment)}. All other gear was stolen by goblin bandits."

    def describe_pray(self, has_shield: bool = False, has_sword: bool = False, has_armor: bool = False) -> str:
        """Generate narrative description of the player praying for restoration.

        Args:
            has_shield: Whether the player has a shield
            has_sword: Whether the player has a sword
            has_armor: Whether the player has any armor pieces
        """
        player_context = self._get_player_context(has_shield, has_sword, has_armor)
        prompt = f"""A holy knight/paladin, injured and weary, kneels to pray for restoration.

{player_context}

Write a vivid 2-3 sentence description of the prayer. Describe how the knight kneels, calls upon their god, and feels the divine light heal their wounds. Be atmospheric and immersive, like a dungeon master narrating a moment of faith.

IMPORTANT: Do NOT mention armor, shield, or sword unless the player actually has them. If they don't have armor, describe them in simple clothing/robes, not armor.

Example style (when no armor):
"You drop to one knee on the cold stone, pressing your hands together in prayer. The words of devotion flow from your lips as you call upon the Light. Warm, golden radiance envelops you, and you feel your wounds knitting closed, your strength returning. The divine power courses through you, and you rise, ready to continue your quest."

Write only the description, no quotes or labels:"""

        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})

        description = self._call_llm(messages, max_tokens=250)
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Prayer for restoration: {description}"
        })
        return description

    def describe_potion_use(self, had_potion: bool) -> str:
        """Generate narrative description of using a health potion."""
        if not had_potion:
            return "You reach for a potion, but your inventory is empty. No healing awaits you."

        prompt = """A holy knight/paladin drinks a health potion during combat or rest.

Write a vivid 2-3 sentence description of drinking the potion. Describe the act of drinking, the taste, and the healing effect. Be atmospheric and immersive, like a dungeon master narrating item use.

Example style:
"You uncork the vial and drink the shimmering liquid in one swift motion. The potion tastes of honey and light, spreading warmth through your body. Your wounds close, your breathing steadies, and strength floods back into your limbs."

Write only the description, no quotes or labels:"""

        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})

        description = self._call_llm(messages, max_tokens=250)
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Potion use: {description}"
        })
        return description

    def describe_flee(self, success: bool, monster_name: str) -> str:
        """Generate narrative description of attempting to flee."""
        prompt = f"""A holy knight/paladin attempts to flee from combat with: {monster_name}

The attempt was {'successful' if success else 'unsuccessful'}.

Write a vivid 2-3 sentence description of the attempt to flee. Be atmospheric and immersive, like a dungeon master narrating escape.

{'Example for success: "You break away from the creature, turning and sprinting down the corridor. The monster\'s snarls fade behind you as you put distance between yourself and danger."' if success else 'Example for failure: "You try to disengage, but the creature is too quick. Its claws rake across your back as you turn, forcing you back into the fight."'}

Write only the description, no quotes or labels:"""

        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})

        description = self._call_llm(messages, max_tokens=250)
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Flee attempt ({'success' if success else 'failed'}): {description}"
        })
        return description

    def describe_encounter(
        self,
        monster_name: str,
        monster_description: str,
        item: Optional[DropResult]
    ) -> str:
        """Generate a full narrative encounter description like a dungeon master.

        Args:
            monster_name: Name of the monster (e.g., "Giant Rat")
            monster_description: Base description of the monster
            item: The item that will drop (None or NO_ITEM means no item)

        Returns:
            A full narrative description of the encounter scene.
        """
        # Determine if item is player's stolen gear or monster's regular loot
        is_player_gear = False
        item_description = ""

        if item is not None and item != DropResult.NO_ITEM:
            # Player's stolen gear: shield, sword, and all armor pieces
            if item in (DropResult.SHIELD, DropResult.SWORD) or item in DropResult.armor_pieces():
                is_player_gear = True
                if item == DropResult.SHIELD:
                    item_description = "a shield"
                elif item == DropResult.SWORD:
                    item_description = "a sword"
                else:
                    # Armor piece
                    item_description = item.name.replace("_", " ").lower()
            else:
                # Regular monster loot (potions, scrolls)
                is_player_gear = False
                item_description = item.name.replace("_", " ").lower()

        items_text = ""
        if item_description:
            if is_player_gear:
                items_text = f"The creature has or is near: {item_description} (this is the player's stolen holy knight gear)"
            else:
                items_text = f"The creature has or is near: {item_description} (this is regular loot the monster has)"

        prompt = f"""You are a dungeon master describing a scene to players. A holy knight/paladin enters a room and encounters:

Monster: {monster_name}
Description: {monster_description}
{f"Items present: {items_text}" if items_text else "No notable items visible."}

IMPORTANT: If the item is marked as "player's stolen holy knight gear" (shield, sword, or any armor piece), describe it as the player's own high-quality equipment that was stolen by goblin bandits. Use phrases like "your gleaming shield", "your blessed sword", "your ornate helm", etc. - these are the paladin's own gear, fit for a holy knight. If the item is marked as "regular loot" (potions, scrolls), describe it as something the monster naturally has or has scavenged.

Write a vivid, atmospheric 2-4 sentence description of this encounter scene. Describe the monster naturally as part of the scene, not as a mechanical announcement.
- Start with the scene/setting (torchlight, shadows, sounds, etc.)
- Describe the monster as the player would see it
- If an item is present, weave it naturally into the description
- Be immersive and atmospheric, like you're telling a story at a tabletop game
- Do NOT start with "Enemy spotted:" or similar mechanical phrases
- Write in second person ("you see", "you notice", etc.)

Example style (with player's gear):
"A massive rat startles at your approach, its whiskers twitching above a shallow pile of scavenged debris. Half-buried there is your shield—its radiant crest muted under dust but unmistakably yours. The creature chitters defensively, as if guarding the strange prize it claimed."

Example style (with monster loot):
"The dim corridor opens into a wider chamber where a skeletal figure stands guard, its hollow eyes fixed on you. In its bony grasp, you notice a small vial of crimson liquid - a health potion, likely scavenged from some unfortunate adventurer."

Write only the description, no quotes or labels:"""

        # Build messages with conversation history for context
        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})

        description = self._call_llm(messages, max_tokens=300)
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Encounter with {monster_name}: {description}"
        })
        return description

    def describe_item_in_context(
        self,
        item: Union[DropResult, str],
        monster_name: str,
        monster_description: str
    ) -> str:
        """Generate creative description using OpenAI."""
        # Extract item name
        if isinstance(item, DropResult):
            if item == DropResult.NO_ITEM:
                return ""
            item_name = item.name.replace("_", " ").lower()
        elif isinstance(item, str):
            item_name = item
        else:
            return ""

        # Build prompt for LLM - include conversation history for context
        prompt = f"""A player encounters a monster:
- Name: {monster_name}
- Description: {monster_description}

The monster will drop: {item_name}

Write a single, creative sentence (15-30 words) describing how this item appears in relation to the monster.
The item is the player's stolen gear (fit for a holy knight), not crude or battered equipment. Consider the monster's nature from its description. Be atmospheric and immersive.

Examples:
- For a wraith with a health potion: "A glass vial glints on the cold stone, left behind by a previous victim."
- For a goblin with a shield: "The goblin brandishes your shield, its holy symbols still visible despite the grime."
- For a skeleton with armor: "Your armor pieces lie scattered among the bones, the goblins having discarded what they couldn't carry."

Write only the sentence, no quotes or extra text:"""

        # Build messages with conversation history for context
        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})

        description = self._call_llm(messages, max_tokens=150)
        # Add the response to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "content": f"Item description for {item_name}: {description}"
        })
        # Ensure it starts with a space if not empty
        return f" {description}" if description else ""
