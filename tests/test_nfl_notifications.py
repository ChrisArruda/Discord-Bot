import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import pytz
import json
from pathlib import Path

# Import the cog we want to test
import sys
import os
sys.path.append(str(Path(__file__).parent.parent))
from discord_bot.cogs.nfl_notifications import NFLNotifications, TEAM_NAME_MAPPING

class TestNFLNotifications(unittest.IsolatedAsyncioTestCase):
    """Test cases for the NFLNotifications cog."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.bot = AsyncMock()
        self.cog = NFLNotifications(self.bot)
        
        # Mock the database
        self.cog.db = MagicMock()
        self.cog.db.load_server_data.return_value = {
            "1234": {
                "teams": {"NFL": "49ers"},
                "notifications": {
                    "enabled": True,
                    "timezone": "America/Los_Angeles",
                    "notify_before_game": 60,
                    "notify_game_start": True,
                    "notify_scores": True,
                    "notify_final_score": True
                }
            },
            "5678": {
                "teams": {"NFL": "Chiefs"},
                "notifications": {
                    "enabled": True,
                    "timezone": "America/Chicago"
                }
            }
        }
        
        # Patch the API methods
        self.mock_session = AsyncMock()
        self.cog.session = self.mock_session
        
        # Create a test guild and user
        self.guild = AsyncMock()
        self.guild.id = 12345
        self.user1 = AsyncMock()
        self.user1.id = 1234
        self.user2 = AsyncMock()
        self.user2.id = 5678
        self.guild.get_member.side_effect = lambda user_id: (
            self.user1 if user_id == 1234 else 
            self.user2 if user_id == 5678 else None
        )
        self.bot.guilds = [self.guild]
    
    async def test_get_upcoming_games(self):
        """Test fetching upcoming games from the API."""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "events": [
                {
                    "id": "401547278",
                    "name": "49ers vs Chiefs",
                    "date": (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
                    "competitions": [
                        {
                            "competitors": [
                                {
                                    "team": {
                                        "id": "25",
                                        "displayName": "San Francisco 49ers",
                                        "abbreviation": "SF"
                                    },
                                    "score": "0"
                                },
                                {
                                    "team": {
                                        "id": "12",
                                        "displayName": "Kansas City Chiefs",
                                        "abbreviation": "KC"
                                    },
                                    "score": "0"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        self.mock_session.get.return_value.__aenter__.return_value = mock_response
        
        # Call the method
        games = await self.cog.get_upcoming_games()
        
        # Assertions
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["name"], "49ers vs Chiefs")
    
    async def test_notification_settings(self):
        """Test notification settings command."""
        # Mock the context
        ctx = AsyncMock()
        ctx.guild.id = 12345
        ctx.author.id = 1234
        
        # Test getting current settings
        await self.cog.notification_settings(ctx)
        ctx.send.assert_called()
        
        # Test updating settings
        ctx.reset_mock()
        await self.cog.notification_settings(ctx, enabled=False, timezone="America/New_York")
        self.cog.db.save_server_data.assert_called()
        ctx.send.assert_called_with("✅ Notification settings updated!", ephemeral=True)
    
    async def test_team_schedule_command(self):
        """Test the team_schedule command."""
        # Mock the context
        ctx = AsyncMock()
        ctx.guild.id = 12345
        
        # Mock the team schedule response
        mock_response = {
            "events": [
                {
                    "id": "401547278",
                    "name": "49ers vs Chiefs",
                    "date": (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
                    "competitions": [
                        {
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
                        }
                    ]
                }
            ]
        }
        
        with patch('discord_bot.cogs.nfl_notifications.NFLNotifications.get_team_schedule', 
                  return_value=mock_response["events"]) as mock_get_schedule:
            await self.cog.team_schedule(ctx, "49ers")
            mock_get_schedule.assert_called_once_with("49ers")
            ctx.send.assert_called()
    
    async def test_notify_upcoming_game(self):
        """Test notification for upcoming games."""
        game = {
            "id": "401547278",
            "name": "49ers vs Chiefs",
            "date": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
            "competitions": [
                {
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
                }
            ]
        }
        
        await self.cog.notify_upcoming_game(game, datetime.utcnow() + timedelta(hours=1), 60)
        
        # Verify notifications were sent to users who follow either team
        self.user1.send.assert_called()
        self.user2.send.assert_called()

if __name__ == "__main__":
    unittest.main()
