"""LLM-powered StoryTeller using OpenAI.

New OpenAI accounts get free credits ($5-18), and gpt-4o-mini is very affordable
(~$0.15 per 1M tokens), so you can play many games for free!
"""

from __future__ import annotations

from typing import Union, List, Optional

# Handle both package and direct imports
try:
    from .models import DropResult, Player
except ImportError:
    from models import DropResult, Player


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

    def _generate_narrative(self, prompt: str, max_tokens: int, history_label: str) -> str:
        """Generate a narrative description using the LLM and update conversation history.

        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum tokens for the response
            history_label: Label for the conversation history entry (e.g., "Combat turn (Holy Smite)")

        Returns:
            The generated narrative description
        """
        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": prompt})

        description = self._call_llm(messages, max_tokens)
        self.conversation_history.append({
            "role": "assistant",
            "content": f"{history_label}: {description}"
        })
        return description

    def track_event(self, event_type: str, description: str) -> None:
        """Add a game event to the conversation history so the LLM remembers it.

        Args:
            event_type: Type of event (e.g., "encounter", "victory", "loot", "game_start", "game_victory", "game_over")
            description: Description of what happened
        """
        # Only track significant events (skip status updates, etc.)
        significant_events = {"encounter", "victory", "loot", "game_start", "game_victory", "game_over"}
        if event_type in significant_events:
            self.conversation_history.append({
                "role": "assistant",
                "content": f"{event_type}: {description}"
            })

    def describe_combat_turn(
        self,
        action: str,
        monster_name: str,
        monster_description: str,
        player_damage: int,
        is_weakness: bool,
        player: Player,
        monster_retaliation_damage: Optional[int] = None,
        player_health_after: Optional[int] = None
    ) -> str:
        """Generate narrative description of a complete combat turn (player action + monster response).

        Args:
            action: The player's action name (e.g., "Holy Smite", "Shield Bash", "Sword Slash")
            monster_name: Name of the monster
            monster_description: Description of the monster
            player_damage: Damage dealt by the player
            is_weakness: Whether the player's attack was a weakness hit
            player: The player object
            monster_retaliation_damage: Damage dealt by monster's retaliation (None if monster died)
            player_health_after: Player's health after monster's attack (None if monster died)
        """
        player_context = self._get_player_context(player)
        weakness_text = " The creature is particularly vulnerable to this attack!" if is_weakness else ""

        retaliation_text = f"\n\nAfter the attack, the {monster_name} retaliates, dealing {monster_retaliation_damage} damage. The player's remaining health is {player_health_after}."

        prompt = f"""A holy knight/paladin is in combat with:
- Monster: {monster_name}
- Description: {monster_description}

{player_context}

The player uses: {action}
Damage dealt: {player_damage}{weakness_text}
The monster survives and retaliates.
{retaliation_text}

Write a vivid 2-4 sentence description of this complete combat exchange. Describe:
1. The player's action (how they strike, the divine power or weapon, the impact)
2. The monster's reaction
3. If the monster survived, describe its counterattack and the player's response
4. If the monster died, describe its final moments

Be cinematic and immersive, like a dungeon master narrating a complete combat turn. Flow naturally from the player's action to the monster's response (or death).

Add emojis appropriately throughout the description to add color and visual interest (e.g., ⚔️ for combat, 🛡️ for shields, ✨ for magic, 💀 for death, etc.).

IMPORTANT: Only mention equipment (shield, sword, armor) if the player actually has it. If they don't have armor, describe them in simple clothing that might be worn under armor, not armor. If they don't have a shield, they can't raise a shield to block.

Example style (monster survives):
"You raise your hand, calling upon the Light, and divine radiance blazes forth, striking the creature with searing holy energy. The monster recoils as the sacred power burns through its form, but it quickly recovers and lunges forward with surprising speed. Claws rake across your clothing as you try to dodge, leaving you winded and bleeding."

Example style (monster dies):
"You raise your hand, fingers outstretched, as the Light gathers around you in a brilliant aura. A surge of divine energy flows through your veins, igniting your spirit with righteous fury. With a thrust of your palm, you unleash a blinding beam of holy power that strikes the giant rat, searing through its matted fur and scorching its flesh. The creature lets out a piercing shriek, its body convulsing under the purifying light, before collapsing to the ground, smoldering and defeated."

Write only the description, no quotes or labels:"""

        return self._generate_narrative(prompt, max_tokens=350, history_label=f"Combat turn ({action})")

    def describe_empty_room(self) -> str:
        """Generate narrative description of a room.

        Returns:
            A vivid description of an empty, quiet space in the dungeon.
        """
        prompt = """A holy knight/paladin enters an empty room of an ancient underground dungeon.
There are no monsters and no items to collect — only the atmosphere of the space itself.

Write a vivid 1-3 sentence description of this empty room.
Focus on environmental detail, mood, remnants of bandit activity, and the quiet tension of a place abandoned in haste.
You may describe old furniture, scattered supplies, broken barricades, makeshift camps, ritual markings, collapsed stonework, or other atmospheric features — but nothing interactable.

Capture the feeling of brief respite mixed with unease, like a dungeon master describing a room between encounters.

Add emojis appropriately throughout the description to add color and visual interest (e.g., 🕯️ for torchlight, 🗝️ for keys, 📜 for scrolls, 🏺 for containers, etc.).

Example style:
"The corridor opens into a cramped study carved into the stone. A toppled desk lies on its side, its drawers yanked out and emptied long ago. Scraps of parchment litter the floor, torn and trampled by both boot and claw."
"You step into a chamber where crude barricades of crates and broken furniture still lean against the walls. Bandits must have tried to fortify this place, but the splintered wood and dried drag marks suggest they didn't hold it for long."
"A small campsite occupies the center of the room—cold ashes in a fire pit, bedrolls slashed open, a tin cup kicked against the far wall. Whatever happened here, it ended abruptly."

Write only the description, with no quotes or labels:
"""

        return self._generate_narrative(prompt, max_tokens=200, history_label="Empty room")

    def describe_loot_find(
        self,
        item: DropResult,
        player: Player
    ) -> str:
        """Generate narrative description of finding loot in a room.

        Args:
            item: The item found (DropResult)
            player: The player object

        Returns:
            A vivid description of finding the item.
        """
        player_context = self._get_player_context(player)

        # Format item name
        if item in DropResult.unique_gear():
            item_name = item.name.replace("_", " ").lower()
            item_type = f"player's stolen gear ({item_name})"
        elif item == DropResult.HEALTH_POTION:
            item_name = "a health potion"
            item_type = "a health potion (regular loot)"
        elif item == DropResult.ESCAPE_SCROLL:
            item_name = "an escape scroll"
            item_type = "an escape scroll (regular loot)"
        else:
            raise ValueError(f"Unexpected item type: {item}")

        is_player_gear = item in DropResult.unique_gear()
        gear_context = " This is the player's own stolen equipment that was taken from them during an ambush. Describe it as high-quality holy knight gear." if is_player_gear else " This is regular loot the player finds."

        prompt = f"""A holy knight/paladin searches a room in the dungeon and finds: {item_type}

{player_context}
{gear_context}

Write a vivid 1-3 sentence description of finding this item. Describe how it's discovered, its condition, and the player's reaction. Be cinematic and immersive, like a dungeon master narrating a discovery.

Add emojis appropriately throughout the description to add color and visual interest (e.g., 🛡️ for shields, 🗡️ for swords, ⚔️ for weapons, 🧪 for potions, 📜 for scrolls, ✨ for magic items, etc.).

IMPORTANT: If it's the player's stolen gear (shield, sword, armor), describe it as their own equipment (e.g., "your shield", "your sword", "your helm"). If it's regular loot (potions, scrolls), describe it as something found.

Example style (player's gear):
"You notice a glint of metal in the corner. As you approach, you recognize the familiar shape of your shield, its radiant emblem still visible beneath a layer of grime. Your fingers close around the cool metal, and a sense of purpose returns to you."

Example style (regular loot):
"Tucked behind a fallen stone, you discover a small vial of crimson liquid. The glass is intact, and the potion within still glimmers with healing magic."

Write only the description, no quotes or labels:"""

        return self._generate_narrative(prompt, max_tokens=250, history_label=f"Loot find ({item_name})")

    def describe_victory(
        self,
        monster_name: str,
        monster_description: str,
        item_acquired: Optional[str],
        player: Player,
        final_action: Optional[str] = None,
        is_weakness: bool = False
    ) -> str:
        """Generate narrative description of defeating a monster.

        Args:
            monster_name: Name of the monster
            monster_description: Description of the monster
            item_acquired: The item being acquired (e.g., "a shield", "health potion") or None
            player: The player object (before acquiring new items)
            final_action: The action that killed the monster (e.g., "Holy Smite", "Shield Bash")
            is_weakness: Whether the final action was a weakness hit
        """
        player_context = self._get_player_context(player)
        items_text = ""
        if item_acquired:
            items_text = f" The creature had: {item_acquired}"

        action_text = ""
        if final_action:
            weakness_text = " (this was a weakness hit - especially effective)" if is_weakness else ""
            action_text = f"\nThe knight defeated it with: {final_action}{weakness_text}"

        prompt = f"""A holy knight/paladin has just defeated a monster with a final blow:
- Monster: {monster_name}
- Description: {monster_description}
{action_text}
{items_text}

{player_context}

Write a vivid 2-4 sentence description that combines BOTH the final attack and the monster's defeat. Describe the attack itself (how the knight strikes), the monster's reaction and final moments, how it falls, and if items are present, how the knight retrieves them. Be cinematic and immersive, like a dungeon master narrating a complete victory scene.

Add emojis appropriately throughout the description to add color and visual interest (e.g., ⚔️ for combat, ✨ for magic, 💀 for death, 🛡️ for shields, 🗡️ for swords, 💎 for treasures, etc.).

IMPORTANT:
- Include the attack description in the narrative (e.g., "You raise your hand and unleash a blinding beam of holy power...")
- Only mention equipment (shield, sword, armor) if the player actually has it or is acquiring it
- If they don't have armor, describe them in simple clothing that might be worn under armor, not armor

Example style:
"You raise your hand, fingers outstretched, as the Light gathers around you in a brilliant aura. A surge of divine energy flows through your veins, igniting your spirit with righteous fury. With a thrust of your palm, you unleash a blinding beam of holy power that strikes the giant rat, searing through its matted fur and scorching its flesh. The creature lets out a piercing shriek, its body convulsing under the purifying light, before collapsing to the ground, smoldering and defeated. As you step closer, your heart races at the sight of your shield, half-buried beneath the rat's remains; you reach down, fingers trembling with anticipation, and grasp the familiar, cool metal, reclaiming a piece of your lost honor."

Write only the description, no quotes or labels:"""

        return self._generate_narrative(prompt, max_tokens=300, history_label=f"Victory over {monster_name}")

    def _get_player_gear_list(self, player: Player) -> List[str]:
        """Get a list of all gear items the player currently has.

        Returns:
            List of gear item names (e.g., ["shield", "sword", "helm", "cuirass"])
        """
        gear_list = []
        if player.has_shield:
            gear_list.append("shield")
        if player.has_sword:
            gear_list.append("sword")
        for armor_piece in player.owned_armor:
            gear_list.append(armor_piece.name.replace("_", " ").lower())
        return gear_list

    def _has_all_gear(self, player: Player) -> bool:
        """Check if the player has recovered all their stolen gear.

        Returns:
            True if player has shield, sword, and all 6 armor pieces
        """
        all_gear = DropResult.unique_gear()
        if not player.has_shield or not player.has_sword:
            return False
        # Check if player has all 6 armor pieces
        armor_pieces = [item for item in all_gear if item not in (DropResult.SHIELD, DropResult.SWORD)]
        return len(player.owned_armor) == len(armor_pieces)

    def _get_player_context(self, player: Player) -> str:
        """Generate context string about the player's current equipment state and health."""
        gear_list = self._get_player_gear_list(player)
        has_all_gear = self._has_all_gear(player)

        if len(gear_list) == 0:
            equipment_text = "IMPORTANT: The player has NO armor, NO shield, and NO sword. All their gear was stolen by goblin bandits. They are wearing only basic clothing that might be worn under armor, not armor."
        elif has_all_gear:
            equipment_text = "The player has recovered ALL of their stolen gear: shield, sword, and all armor pieces. They are now fully equipped as a holy knight. Only the Heart of Radiance (the holy relic) remains to be recovered from the final boss."
        else:
            equipment_text = f"The player currently has: {', '.join(gear_list)}. They are still missing some of their stolen gear."

        # Add health information
        health_percent = (player.health / player.max_health) * 100
        if health_percent <= 25:
            health_status = "The player is critically injured and barely standing, moving with great difficulty."
        elif health_percent <= 50:
            health_status = "The player is badly wounded, moving slowly and with visible pain."
        elif health_percent <= 75:
            health_status = "The player is moderately injured but still capable of fighting."
        else:
            health_status = "The player is in good condition, with only minor wounds."

        return f"{equipment_text}\n\nHealth: {player.health}/{player.max_health} HP. {health_status}"

    def describe_pray(self, player: Player) -> str:
        """Generate narrative description of the player praying for restoration.

        Args:
            player: The player object
        """
        player_context = self._get_player_context(player)
        prompt = f"""A holy knight/paladin, injured and weary, kneels to pray for restoration.

{player_context}

Write a vivid 1-3 sentence description of the prayer. Describe how the knight kneels, calls upon their god, and feels the divine light heal their wounds. Be atmospheric and immersive, like a dungeon master narrating a moment of faith.

Add emojis appropriately throughout the description to add color and visual interest (e.g., ✨ for divine light, 🙏 for prayer, 💫 for healing, ⚡ for divine power, etc.).

IMPORTANT: Do NOT mention armor, shield, or sword unless the player actually has them. If they don't have armor, describe them in simple clothing that might be worn under armor, not armor.

Example style (when no armor):
"You drop to one knee on the cold stone, pressing your hands together in prayer. The words of devotion flow from your lips as you call upon the Light. Warm, golden radiance envelops you, and you feel your wounds knitting closed, your strength returning. The divine power courses through you, and you rise, ready to continue your quest."

Write only the description, no quotes or labels:"""

        return self._generate_narrative(prompt, max_tokens=250, history_label="Prayer for restoration")

    def describe_all_gear_recovered(self, player: Player) -> str:
        """Generate narrative description when the player recovers the final piece of gear.

        Args:
            player: The player object (who has just recovered all gear)

        Returns:
            A vivid description of the moment of complete recovery.
        """
        player_context = self._get_player_context(player)

        prompt = f"""A holy knight/paladin has just recovered the final piece of their stolen gear. They now have ALL of their equipment back: shield, sword, and all armor pieces.

{player_context}

Write a vivid 2-4 sentence description of this momentous occasion. The knight should feel a surge of hope and determination. They have recovered everything that was stolen from them - their complete holy knight's regalia. Now, only one thing remains: the Heart of Radiance, the sacred relic that the final boss holds. The knight should feel ready for the final confrontation, knowing that with all their gear restored, they can face the ultimate challenge.

Be emotional and triumphant, but also focused on the final goal. This is a turning point in their journey.

Add emojis appropriately throughout the description to add color and visual interest (e.g., ✨ for triumph, 🛡️ for armor, ⚔️ for readiness, 💎 for the relic, 🌟 for hope, etc.).

Example style:
"You feel the weight of the final piece settle into place, and suddenly, you are whole again. Every piece of your stolen regalia has been reclaimed - your shield, your sword, your helm, your armor. The familiar weight of your complete holy knight's equipment fills you with a sense of purpose you haven't felt since the ambush. You stand tall, fully restored, and your gaze turns toward the deeper darkness where the final boss awaits. The Heart of Radiance calls to you, and you are ready to answer."

Write only the description, no quotes or labels:"""

        return self._generate_narrative(prompt, max_tokens=300, history_label="All gear recovered")

    def describe_potion_use(self, player: Player) -> str:
        """Generate narrative description of using a health potion."""
        player_context = self._get_player_context(player)

        prompt = f"""A holy knight/paladin drinks a health potion during combat or rest.

{player_context}

Write a vivid 1-3 sentence description of drinking the potion. Describe the act of drinking, the taste, and the healing effect. Be atmospheric and immersive, like a dungeon master narrating item use.

Add emojis appropriately throughout the description to add color and visual interest (e.g., 🧪 for potions, ✨ for healing magic, 💚 for health, 💫 for restoration, etc.).

Example style:
"You uncork the vial and drink the shimmering liquid in one swift motion. The potion tastes of honey and light, spreading warmth through your body. Your wounds close, your breathing steadies, and strength floods back into your limbs."

Write only the description, no quotes or labels:"""

        return self._generate_narrative(prompt, max_tokens=250, history_label="Potion use")

    def describe_flee(self, success: bool, monster_name: str) -> str:
        """Generate narrative description of attempting to flee."""
        prompt = f"""A holy knight/paladin attempts to flee from combat with: {monster_name}

The attempt was {'successful' if success else 'unsuccessful'}.

Write a vivid 1-3 sentence description of the attempt to flee. Be atmospheric and immersive, like a dungeon master narrating escape.

Add emojis appropriately throughout the description to add color and visual interest (e.g., 🏃 for running, 💨 for speed, ⚠️ for danger, etc.).

{'Example for success: "You break away from the creature, turning and sprinting down the corridor. The monster\'s snarls fade behind you as you put distance between yourself and danger."' if success else 'Example for failure: "You try to disengage, but the creature is too quick. Its claws rake across your back as you turn, forcing you back into the fight."'}

Write only the description, no quotes or labels:"""

        return self._generate_narrative(
            prompt,
            max_tokens=250,
            history_label=f"Flee attempt ({'success' if success else 'failed'})"
        )

    def describe_encounter(
        self,
        monster_name: str,
        monster_description: str,
        item: Optional[DropResult],
        player: Player
    ) -> str:
        """Generate a full narrative encounter description like a dungeon master.

        Args:
            monster_name: Name of the monster (e.g., "Giant Rat")
            monster_description: Base description of the monster
            item: The item that will drop (None or NO_ITEM means no item)
            player: The player object

        Returns:
            A full narrative description of the encounter scene.
        """
        player_context = self._get_player_context(player)
        # Determine if item is player's stolen gear or monster's regular loot
        is_player_gear = False
        item_description = ""

        if item is not None and item != DropResult.NO_ITEM:
            # Player's stolen gear: shield, sword, and all armor pieces
            is_player_gear = item in DropResult.unique_gear()
            if item == DropResult.SHIELD:
                item_description = "a shield"
            elif item == DropResult.SWORD:
                item_description = "a sword"
            else:
                # Armor piece or regular loot
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

{player_context}

IMPORTANT: If the item is marked as "player's stolen holy knight gear" (shield, sword, or any armor piece), describe it as the player's own high-quality equipment that was stolen by goblin bandits. Use phrases like "your gleaming shield", "your blessed sword", "your ornate helm", etc. - these are the paladin's own gear, fit for a holy knight. If the item is marked as "regular loot" (potions, scrolls), describe it as something the monster naturally has or has scavenged.

Write a vivid, atmospheric 1-4 sentence description of this encounter scene. Describe the monster naturally as part of the scene, not as a mechanical announcement.
- Start with the scene/setting (torchlight, shadows, sounds, etc.)
- Describe the monster as the player would see it
- If an item is present, weave it naturally into the description
- Be immersive and atmospheric, like you're telling a story at a tabletop game
- Do NOT start with "Enemy spotted:" or similar mechanical phrases
- Write in second person ("you see", "you notice", etc.)

Add emojis appropriately throughout the description to add color and visual interest (e.g., 🕯️ for torchlight, 👹 for monsters, 🛡️ for shields, 🗡️ for swords, 🧪 for potions, 💀 for skeletons, etc.).

Example style (with player's gear):
"A massive rat startles at your approach, its whiskers twitching above a shallow pile of scavenged debris. Half-buried there is your shield—its radiant crest muted under dust but unmistakably yours. The creature chitters defensively, as if guarding the strange prize it claimed."

Example style (with monster loot):
"The dim corridor opens into a wider chamber where a skeletal figure stands guard, its hollow eyes fixed on you. In its bony grasp, you notice a small vial of crimson liquid - a health potion, likely scavenged from some unfortunate adventurer."

Write only the description, no quotes or labels:"""

        return self._generate_narrative(prompt, max_tokens=300, history_label=f"Encounter with {monster_name}")
