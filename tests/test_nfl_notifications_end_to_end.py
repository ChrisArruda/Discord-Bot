#!/usr/bin/env python3
"""
End-to-end test for NFL Notifications.

This script tests the complete flow of the NFL notification system,
including database interactions, API calls, and Discord message sending.
"""
import asyncio
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
import discord
from discord.ext import commands
import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Import the cog we want to test
from discord_bot.cogs.nfl_notifications import NFLNotifications
from discord_bot.cogs.teams import Teams
from discord_bot.utils.database import Database
from discord_bot.config import DATA_DIR, VALID_LEAGUES

# Test configuration
TEST_GUILD_ID = 12345
TEST_CHANNEL_ID = 98765
TEST_USER_IDS = [1111, 2222, 3333]
TEST_TEAMS = ["49ers", "Chiefs", "Packers"]

# Mock Discord objects
class MockMember:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.mention = f"<@{id}>"
        self.display_name = name
        self.dm_channel = None
    
    async def send(self, *args, **kwargs):
        print(f"[MOCK DM to {self.name}] {args[0] if args else ''}")
        return None
    
    async def create_dm(self):
        self.dm_channel = self
        return self

class MockGuild:
    def __init__(self, id):
        self.id = id
        self.members = []
    
    def get_member(self, user_id):
        for member in self.members:
            if member.id == user_id:
                return member
        return None

class MockContext:
    def __init__(self, bot, author, guild, channel):
        self.bot = bot
        self.author = author
        self.guild = guild
        self.channel = channel
        self.message = AsyncMock()
        self.send = AsyncMock()
        self.respond = AsyncMock()
        self.interaction = AsyncMock()
        self.interaction.response = AsyncMock()
        self.interaction.followup = AsyncMock()

# Test fixtures
@pytest.fixture(scope="module")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def bot():
    """Create a bot instance for testing."""
    intents = discord.Intents.default()
    intents.members = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    # Add database and cogs
    bot.db = Database()
    await bot.add_cog(Teams(bot))
    await bot.add_cog(NFLNotifications(bot))
    
    # Setup test guild and users
    guild = MockGuild(TEST_GUILD_ID)
    bot.guilds = [guild]
    
    # Create test users
    users = [MockMember(uid, f"TestUser{i}") for i, uid in enumerate(TEST_USER_IDS, 1)]
    guild.members = users
    
    # Setup test channel
    channel = AsyncMock()
    channel.id = TEST_CHANNEL_ID
    channel.guild = guild
    bot.get_channel = AsyncMock(return_value=channel)
    
    yield bot
    
    # Cleanup
    if hasattr(bot, 'session') and not bot.session.closed:
        await bot.session.close()

@pytest.mark.asyncio
async def test_end_to_end_flow(bot):
    """Test the complete flow of the NFL notification system."""
    # Setup test context
    guild = bot.guilds[0]
    user = guild.get_member(TEST_USER_IDS[0])
    channel = bot.get_channel(TEST_CHANNEL_ID)
    ctx = MockContext(bot, user, guild, channel)
    
    # Get the cogs
    teams_cog = bot.get_cog("Teams")
    nfl_cog = bot.get_cog("NFLNotifications")
    
    # Test 1: User sets their favorite team
    await teams_cog.set_team(ctx, "NFL", "49ers")
    ctx.send.assert_called_with("✅ Set your favorite NFL team to 49ers!")
    
    # Test 2: User configures notification settings
    ctx.send.reset_mock()
    await nfl_cog.notification_settings(ctx, timezone="America/Los_Angeles", notify_before=60)
    ctx.send.assert_called_with("✅ Notification settings updated!", ephemeral=True)
    
    # Test 3: Check team schedule
    ctx.send.reset_mock()
    with patch.object(nfl_cog, 'get_team_schedule') as mock_schedule:
        # Mock the API response
        mock_schedule.return_value = [{
            "id": "401547278",
            "name": "49ers vs Chiefs",
            "date": (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            "competitions": [{
                "competitors": [
                    {
                        "team": {
                            "displayName": "San Francisco 49ers",
                            "abbreviation": "SF"
                        },
                        "score": "0"
                    },
                    {
                        "team": {
                            "displayName": "Kansas City Chiefs",
                            "abbreviation": "KC"
                        },
                        "score": "0"
                    }
                ]
            }]
        }]
        
        await nfl_cog.team_schedule(ctx, "49ers")
        ctx.send.assert_called()
    
    # Test 4: Simulate game check (would be done by the background task)
    game = {
        "id": "401547278",
        "name": "49ers vs Chiefs",
        "date": (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z",
        "competitions": [{
            "competitors": [
                {
                    "team": {
                        "displayName": "San Francisco 49ers",
                        "abbreviation": "SF",
                        "logos": [{"href": "http://example.com/49ers.png"}]
                    },
                    "score": "0"
                },
                {
                    "team": {
                        "displayName": "Kansas City Chiefs",
                        "abbreviation": "KC"
                    },
                    "score": "0"
                }
            ]
        }]
    }
    
    # This would normally be called by the background task
    await nfl_cog.notify_upcoming_game(game, datetime.utcnow() + timedelta(minutes=30), 30)
    
    # Verify the user was notified
    assert user.dm_channel is not None
    # Note: In a real test, we would verify the actual message content

if __name__ == "__main__":
    # Run the tests
    import sys
    sys.exit(pytest.main([__file__] + sys.argv[1:]))
