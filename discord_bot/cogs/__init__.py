# This file makes the cogs directory a Python package
# This file makes the cogs directory a Python package
from .nfl_notifications import NFLNotifications

async def setup(bot):
    """Load all cogs."""
    await bot.add_cog(NFLNotifications(bot))
