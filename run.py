#!/usr/bin/env python3
"""
Run script for the Discord bot.
"""
import os
import sys
from dotenv import load_dotenv

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath('.'))

# Load environment variables
load_dotenv()

# Import and run the bot
from discord_bot.bot import bot

if __name__ == "__main__":
    # Ensure the bot has a token
    if not os.getenv("DISCORD_TOKEN"):
        print("Error: No Discord token found. Please set the DISCORD_TOKEN environment variable in a .env file.")
        sys.exit(1)
    
    # Run the bot
    try:
        bot.run(os.getenv("DISCORD_TOKEN"))
    except Exception as e:
        print(f"Error starting bot: {e}")
        sys.exit(1)
