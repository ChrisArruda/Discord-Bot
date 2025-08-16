import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# Import configuration and utilities
from .config import TOKEN, PREFIX, DATA_DIR
from .utils.database import db

# Set up intents
intents = discord.Intents.default()
intents.message_content = True  # Required for prefix commands
intents.messages = True         # Required for message events
intents.guilds = True           # Required for guild events

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(PREFIX),
            intents=intents,
            help_command=commands.DefaultHelpCommand(no_category='Commands'),
            activity=discord.Game(name=f"Type {PREFIX}help")
        )
        self.start_time = datetime.utcnow()
        self.games = {}  # In-memory game storage

    async def setup_hook(self):
        """Load all cogs when the bot starts."""
        # Get the directory where this file is located
        cogs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cogs')
        
        # Load all .py files in the cogs directory
        for filename in os.listdir(cogs_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                try:
                    await self.load_extension(f"discord_bot.cogs.{filename[:-3]}")
                    print(f"Loaded cog: {filename}")
                except Exception as e:
                    print(f"Failed to load cog {filename}: {e}")

    async def on_ready(self):
        """Event triggered when the bot is ready."""
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("------")
        
        # Sync application commands
        print("Syncing application commands...")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync application commands: {e}")

# Create bot instance
bot = MyBot()

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore command not found errors
    
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f" Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(" Invalid argument provided.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(" You don't have permission to use this command.")
    else:
        await ctx.send(f" An error occurred: {str(error)}")
        # Print the full traceback to console
        import traceback
        traceback.print_exception(type(error), error, error.__traceback__)

# Run the bot
if __name__ == "__main__":
    # Ensure environment variables are loaded
    load_dotenv()
    
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    # Run the bot
    bot.run(TOKEN)
