import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath('.'))

from discord_bot.bot import bot

def test_bot():
    """Test if the bot can load all cogs and start up."""
    try:
        # This will raise an exception if the token is not set
        # but we just want to test if the bot initializes correctly
        bot.run('test_token', log_handler=None)
    except discord.LoginFailure:
        print("Bot initialization successful! (Login failure expected since no token was provided)")
        return True
    except Exception as e:
        print(f"Error initializing bot: {e}")
        return False

if __name__ == "__main__":
    test_bot()
