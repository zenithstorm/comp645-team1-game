# Dungeon Crawler Game

A text-based dungeon crawler game with AI-powered narrative generation using OpenAI.

## Prerequisites

### Installing Python

**Windows:**
1. Download Python from https://www.python.org/downloads/
2. Run the installer
3. **Important**: Check the box "Add Python to PATH" during installation
4. Click "Install Now"

**macOS:**
- Python 3 is usually pre-installed. Check by running: `python3 --version`
- If not installed, download from https://www.python.org/downloads/ or use Homebrew:
  ```bash
  brew install python3
  ```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip

# Fedora
sudo dnf install python3 python3-pip

# Arch Linux
sudo pacman -S python python-pip
```

### Verify Installation

Open a terminal and verify Python is installed:

```bash
python --version
# or: python3 --version
# or on Windows: py --version
```

You should see `Python 3.11.0` or higher.

## Quick Start

1. **Install OpenAI package:**
   ```bash
   # Windows (Git Bash/CMD)
   py -m pip install openai

   # macOS/Linux
   pip install openai
   # or: pip3 install openai
   ```

2. **Get an OpenAI API key:**
   - Sign up at https://platform.openai.com
   - New accounts get **free credits ($5-18)** to get started!
   - Create an API key in your account settings

3. **Set your API key:**
   Windows CMD: `set OPENAI_API_KEY=your-api-key-here`
   Linux/Mac: `export OPENAI_API_KEY="your-api-key-here"`

4. **Run the game:**
   ```bash
   python run_game.py
   # or: python3 run_game.py
   # or on Windows: py run_game.py
   ```

## Cost

- **New accounts**: Get $5-18 in free credits (plenty for many games!)
- **gpt-4o-mini** (default): ~$0.15 per 1M tokens
- **Typical game session**: ~$0.01-0.02 (10-20 monster encounters)
- You can play **hundreds of games** on the free credits!

## How It Works

The AI generates creative, atmospheric descriptions of area, items, and monsters for an immersive narrative experience.

## Gameplay

- Explore rooms and fight monsters
- Collect loot (potions, scrolls, armor)
- Unlock new abilities (shield, sword)
- Defeat the boss to win

## Project Structure

- `run_game.py` - Main entry point (requires OpenAI API key)
- `systems.py` - Core game logic
- `models.py` - Game entities (Player, Monster, etc.)
- `config.py` - Game configuration
- `ui.py` - User interface
- `llm_storyteller.py` - OpenAI StoryTeller implementation

## Customization

### Changing the AI Model

Edit `run_game.py` and change the model parameter:

```python
storyteller = LLMStoryTeller(api_key=api_key, model="gpt-4")  # Better quality, more expensive
# or
storyteller = LLMStoryTeller(api_key=api_key, model="gpt-3.5-turbo")  # Faster, cheaper
```

### Adjusting Game Balance

Edit `config.py` to tune:
- Player/monster stats
- Drop rates
- Boss spawn conditions
- Combat damage values
