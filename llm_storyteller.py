"""LLM-powered StoryTeller using OpenAI.

New OpenAI accounts get free credits ($5-18), and gpt-4o-mini is very affordable
(~$0.15 per 1M tokens), so you can play many games for free!
"""

from __future__ import annotations

from typing import Union, List

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
        if context.startswith(("encounter:", "victory:", "loot:", "game:")):
            self.add_game_event(context)
        return context.strip()

    def describe_encounter(
        self,
        monster_name: str,
        monster_description: str,
        items: List[Union[DropResult, str]]
    ) -> str:
        """Generate a full narrative encounter description like a dungeon master.

        Args:
            monster_name: Name of the monster (e.g., "Giant Rat")
            monster_description: Base description of the monster
            items: List of items that will be dropped (shields, swords, potions, etc.)

        Returns:
            A full narrative description of the encounter scene.
        """
        # Build list of item names
        item_names = []
        for item in items:
            if isinstance(item, DropResult):
                if item != DropResult.NO_ITEM:
                    item_names.append(item.name.replace("_", " ").lower())
            elif isinstance(item, str):
                item_names.append(item)

        items_text = ""
        if item_names:
            if len(item_names) == 1:
                items_text = f"The creature has or is near: {item_names[0]}"
            elif len(item_names) == 2:
                items_text = f"The creature has or is near: {item_names[0]} and {item_names[1]}"
            else:
                items_text = f"The creature has or is near: {', '.join(item_names[:-1])}, and {item_names[-1]}"

        prompt = f"""You are a dungeon master describing a scene to players. A holy knight/paladin enters a room and encounters:

Monster: {monster_name}
Description: {monster_description}
{f"Items present: {items_text}" if items_text else "No notable items visible."}

Write a vivid, atmospheric 2-4 sentence description of this encounter scene. Describe the monster naturally as part of the scene, not as a mechanical announcement. 
- Start with the scene/setting (torchlight, shadows, sounds, etc.)
- Describe the monster as the player would see it
- If items are present, weave them naturally into the description (these are the player's stolen gear, fit for a holy knight)
- Be immersive and atmospheric, like you're telling a story at a tabletop game
- Do NOT start with "Enemy spotted:" or similar mechanical phrases
- Write in second person ("you see", "you notice", etc.)

Example style:
"The torchlight flickers as you round the corner, revealing a massive rat with patchy fur and prominent incisors. It scuttles nervously, low to the ground, always testing distance. The creature drags your gleaming shield behind it, the radiant emblem of your order dulled by dirt but still flickering with remnants of divine light."

Write only the description, no quotes or labels:"""

        # Build messages with conversation history for context
        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,
                temperature=0.8,
            )
            description = response.choices[0].message.content.strip()
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": f"Encounter with {monster_name}: {description}"
            })
            return description
        except Exception as e:
            # Check if it's a quota/rate limit error
            error_str = str(e).lower()
            error_type = type(e).__name__
            # Check for insufficient quota errors
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
            # Re-raise other errors (they'll be caught by the try/except in systems.py)
            raise

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
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=60,
                temperature=0.8,
            )
            # Add the response to conversation history
            description = response.choices[0].message.content.strip()
            self.conversation_history.append({
                "role": "assistant",
                "content": f"Item description for {item_name}: {description}"
            })
            description = response.choices[0].message.content.strip()
            # Ensure it starts with a space if not empty
            return f" {description}" if description else ""
        except Exception as e:
            # Check if it's a quota/rate limit error
            error_str = str(e).lower()
            error_type = type(e).__name__
            # Check for insufficient quota errors
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
            # Re-raise other errors (they'll be caught by the try/except in systems.py)
            raise

