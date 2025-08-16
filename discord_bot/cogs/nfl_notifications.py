import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional
import aiohttp
import discord
import pytz
from discord.ext import commands, tasks

from ..utils.json_store import json_store
from ..utils.schedules import Game, EspnNflProvider, MockNflProvider

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = pytz.timezone("America/Los_Angeles")
DEFAULT_NOTIFY_TIME = time(9, 0)  # 9:00 AM
DEFAULT_WINDOW_DAYS = 3

class NFLNotifications(commands.Cog):
    """NFL game notifications for Discord servers."""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.provider = self._get_provider()
        self.notification_loop.start()
    
    def cog_unload(self):
        self.notification_loop.cancel()
        asyncio.create_task(self.session.close())
    
    def _get_provider(self):
        """Get the appropriate schedule provider based on configuration."""
        # In a real implementation, this would check config
        return EspnNflProvider(self.session)
    
    async def _get_guild_data(self, guild_id: int) -> Dict:
        """Get or initialize guild data."""
        filepath = f"data/guilds/{guild_id}.json"
        data = await json_store.read(filepath)
        
        if not data:
            data = {
                "guild_id": str(guild_id),
                "channels": {"NFL": None},
                "users": {}
            }
            await json_store.write(filepath, data)
        
        return data
    
    async def _save_guild_data(self, guild_id: int, data: Dict) -> bool:
        """Save guild data."""
        filepath = f"data/guilds/{guild_id}.json"
        return await json_store.write(filepath, data)
    
    @tasks.loop(time=DEFAULT_NOTIFY_TIME, timezone=DEFAULT_TIMEZONE)
    async def notification_loop(self):
        """Background task to send daily notifications."""
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            try:
                await self._process_guild_notifications(guild)
            except Exception as e:
                logger.error(f"Error processing notifications for guild {guild.id}: {e}")
    
    async def _process_guild_notifications(self, guild: discord.Guild):
        """Process notifications for a single guild."""
        data = await self._get_guild_data(guild.id)
        channel_id = data.get('channels', {}).get('NFL')
        
        if not channel_id:
            return
            
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return
            
        for user_id, user_data in data.get('users', {}).items():
            try:
                await self._process_user_notifications(user_id, user_data, channel)
            except Exception as e:
                logger.error(f"Error processing user {user_id} in guild {guild.id}: {e}")
    
    async def _process_user_notifications(self, user_id: str, user_data: Dict, channel: discord.TextChannel):
        """Process notifications for a single user."""
        notifications = user_data.get('notifications', {}).get('NFL', {})
        
        if not notifications.get('enabled', False):
            return
            
        team = user_data.get('teams', {}).get('NFL')
        if not team:
            return
            
        # Calculate date range
        now = datetime.now(DEFAULT_TIMEZONE)
        window_days = notifications.get('window_days', DEFAULT_WINDOW_DAYS)
        end_date = now + timedelta(days=window_days)
        
        # Get upcoming games
        games = await self.provider.get_upcoming_games(
            team=team,
            start_date=now,
            end_date=end_date
        )
        
        # Filter out already notified games
        last_sent = set(notifications.get('last_sent_game_ids', []))
        new_games = [g for g in games if g.game_id not in last_sent]
        
        if not new_games:
            return
            
        # Send notifications
        user = self.bot.get_user(int(user_id))
        if not user:
            return
            
        for game in new_games:
            embed = self._create_game_embed(game)
            try:
                await channel.send(f"🔔 {user.mention} - Upcoming game:", embed=embed)
                last_sent.add(game.game_id)
            except discord.HTTPException as e:
                logger.error(f"Failed to send notification to {user_id}: {e}")
        
        # Update last sent games
        guild_data = await self._get_guild_data(channel.guild.id)
        user_data = guild_data['users'].setdefault(user_id, {})
        nfl_notifications = user_data.setdefault('notifications', {}).setdefault('NFL', {})
        nfl_notifications['last_sent_game_ids'] = list(last_sent)
        await self._save_guild_data(channel.guild.id, guild_data)
    
    def _create_game_embed(self, game: Game) -> discord.Embed:
        """Create an embed for a game notification."""
        game_time = game.start_time_utc.astimezone(DEFAULT_TIMEZONE)
        
        embed = discord.Embed(
            title=f"🏈 {game.away_team} @ {game.home_team}",
            description=f"**When:** {discord.utils.format_dt(game_time, 'f')}\n"
                      f"**Where:** {game.venue or 'TBD'}",
            color=discord.Color.blue()
        )
        
        embed.set_footer(text="Game time is displayed in your local timezone")
        return embed
    
    # Command groups
    @commands.group(name="notify", invoke_without_command=True)
    async def notify(self, ctx):
        """Manage game notifications."""
        await ctx.send_help("notify")
    
    @notify.group(name="nfl", invoke_without_command=True)
    async def nfl_notify(self, ctx):
        """Manage NFL game notifications."""
        await ctx.send_help("notify nfl")
    
    # Subcommands
    @nfl_notify.command(name="on")
    async def nfl_notify_on(self, ctx):
        """Enable NFL game notifications."""
        guild_data = await self._get_guild_data(ctx.guild.id)
        user_data = guild_data['users'].setdefault(str(ctx.author.id), {})
        notifications = user_data.setdefault('notifications', {}).setdefault('NFL', {})
        notifications['enabled'] = True
        
        if await self._save_guild_data(ctx.guild.id, guild_data):
            await ctx.send("✅ NFL game notifications enabled!")
        else:
            await ctx.send("❌ Failed to update settings. Please try again.")
    
    @nfl_notify.command(name="off")
    async def nfl_notify_off(self, ctx):
        """Disable NFL game notifications."""
        guild_data = await self._get_guild_data(ctx.guild.id)
        user_data = guild_data['users'].setdefault(str(ctx.author.id), {})
        notifications = user_data.setdefault('notifications', {}).setdefault('NFL', {})
        notifications['enabled'] = False
        
        if await self._save_guild_data(ctx.guild.id, guild_data):
            await ctx.send("🔕 NFL game notifications disabled.")
        else:
            await ctx.send("❌ Failed to update settings. Please try again.")
    
    @nfl_notify.command(name="time")
    async def set_notify_time(self, ctx, time_str: str):
        """Set notification time (HH:MM in 24h format)."""
        try:
            # Parse time string
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time")
                
            guild_data = await self._get_guild_data(ctx.guild.id)
            user_data = guild_data['users'].setdefault(str(ctx.author.id), {})
            notifications = user_data.setdefault('notifications', {}).setdefault('NFL', {})
            notifications['notify_time'] = f"{hour:02d}:{minute:02d}"
            
            if await self._save_guild_data(ctx.guild.id, guild_data):
                await ctx.send(f"⏰ Notification time set to {time_str} (server time)")
            else:
                await ctx.send("❌ Failed to update settings. Please try again.")
                
        except (ValueError, IndexError):
            await ctx.send("❌ Invalid time format. Use HH:MM (24-hour format)")
    
    @nfl_notify.command(name="window")
    async def set_notify_window(self, ctx, days: int):
        """Set notification window (1-7 days)."""
        if not 1 <= days <= 7:
            await ctx.send("❌ Window must be between 1 and 7 days")
            return
            
        guild_data = await self._get_guild_data(ctx.guild.id)
        user_data = guild_data['users'].setdefault(str(ctx.author.id), {})
        notifications = user_data.setdefault('notifications', {}).setdefault('NFL', {})
        notifications['window_days'] = days
        
        if await self._save_guild_data(ctx.guild.id, guild_data):
            await ctx.send(f"📅 Notification window set to {days} days")
        else:
            await ctx.send("❌ Failed to update settings. Please try again.")
    
    @nfl_notify.command(name="channel")
    @commands.has_permissions(manage_guild=True)
    async def set_notify_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the notification channel (requires Manage Server)."""
        guild_data = await self._get_guild_data(ctx.guild.id)
        
        if channel is None:
            guild_data['channels']['NFL'] = ctx.channel.id
            message = f"📢 Notifications will be sent in this channel"
        else:
            guild_data['channels']['NFL'] = channel.id
            message = f"📢 Notifications will be sent to {channel.mention}"
        
        if await self._save_guild_data(ctx.guild.id, guild_data):
            await ctx.send(f"✅ {message}")
        else:
            await ctx.send("❌ Failed to update notification channel")
    
    @nfl_notify.command(name="test")
    async def test_notification(self, ctx):
        """Send a test notification."""
        guild_data = await self._get_guild_data(ctx.guild.id)
        user_data = guild_data['users'].get(str(ctx.author.id), {})
        team = user_data.get('teams', {}).get('NFL')
        
        if not team:
            await ctx.send("❌ You haven't set your NFL team yet. Use `!team set NFL <team>` first.")
            return
            
        # Create a test game
        now = datetime.now(DEFAULT_TIMEZONE)
        test_game = Game(
            home_team="Home Team",
            away_team="Away Team",
            start_time_utc=now + timedelta(days=1),
            venue="Test Stadium",
            game_id="test-123"
        )
        
        embed = self._create_game_embed(test_game)
        await ctx.send("🔔 **Test Notification** - This is what a game notification looks like:", embed=embed)
    
    # Error handlers
    @set_notify_channel.error
    async def set_notify_channel_error(self, ctx, error):
        """Handle errors for the set_notify_channel command."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You need the 'Manage Server' permission to change the notification channel.")
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send("❌ Channel not found. Please mention a valid text channel.")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")
    
    @notification_loop.before_loop
    async def before_notification_loop(self):
        """Wait for the bot to be ready before starting the loop."""
        await self.bot.wait_ready()

async def setup(bot):
    """Load the NFL notifications cog."""
    await bot.add_cog(NFLNotifications(bot))
