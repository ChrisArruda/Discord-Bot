import asyncio
import logging
from datetime import datetime, time, timedelta, timezone
import pytz
from typing import Dict, List, Optional, Set, Tuple
import aiohttp
import discord
import pytz
from discord.ext import commands, tasks

from ..utils.schedules import Game, EspnNflProvider, MockNflProvider
from ..utils.database import db

logger = logging.getLogger(__name__)

# Constants
# Time is in Pacific Time (manually adjusted for DST if needed)
DEFAULT_NOTIFY_TIME = time(9, 0)  # 9:00 AM PT
DEFAULT_WINDOW_DAYS = 3
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
RATE_LIMIT = 20  # Max requests per minute

class NFLNotifications(commands.Cog):
    """NFL game notifications for Discord servers."""
    
    def __init__(self, bot):
        self.bot = bot
        
    def cog_load(self):
        """Start the notification loop when the cog is loaded."""
        try:
            self.notification_loop.start()
        except RuntimeError:
            logger.warning("Notification loop is already running")
            
    def cog_unload(self):
        """Stop the notification loop and clean up resources when the cog is unloaded."""
        self.notification_loop.cancel()
        if hasattr(self, 'session') and self.session and not self.session.closed:
            asyncio.create_task(self.session.close())
    
    def _get_provider(self):
        """Get the appropriate schedule provider based on configuration."""
        # In a real implementation, this would check config
        return EspnNflProvider(self.session)
        
    async def _make_api_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make an HTTP request with rate limiting and retries."""
        headers = {
            'User-Agent': 'DiscordBot/1.0',
            'Accept': 'application/json'
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                # Check rate limits
                now = time.time()
                endpoint = url.split('?')[0]  # Basic endpoint tracking
                
                if endpoint in self._rate_limits:
                    last_call, count = self._rate_limits[endpoint]
                    if now - last_call < 60 and count >= RATE_LIMIT:  # 60 seconds window
                        wait_time = 60 - (now - last_call)
                        logger.warning(f"Rate limit reached for {endpoint}, waiting {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)
                        self._rate_limits[endpoint] = (time.time(), 1)
                
                async with self.session.get(url, params=params, headers=headers) as response:
                    # Update rate limit tracking
                    self._rate_limits[endpoint] = (time.time(), 
                        self._rate_limits.get(endpoint, (0, 0))[1] + 1)
                    
                    if response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get('Retry-After', RETRY_DELAY))
                        logger.warning(f"Rate limited, retrying after {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                        
                    response.raise_for_status()
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                logger.error(f"API request failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    raise
                    
        return None
    
    async def _get_guild_data(self, guild_id: int) -> Dict:
        """Get or initialize guild data."""
        # Use the database to load server data
        data = db.load_server_data(guild_id)
        
        # Ensure the data has the expected structure
        if 'guild_id' not in data:
            data['guild_id'] = str(guild_id)
        if 'channels' not in data:
            data['channels'] = {'NFL': None}
        if 'users' not in data:
            data['users'] = {}
            
        return data
    
    async def _save_guild_data(self, guild_id: int, data: Dict) -> bool:
        """Save guild data."""
        # Use the database to save server data
        return db.save_server_data(guild_id, data)
    
    @tasks.loop(time=DEFAULT_NOTIFY_TIME)
    async def notification_loop(self):
        """Background task to send daily notifications."""
        await self.bot.wait_until_ready()
        
        for guild in self.bot.guilds:
            try:
                await self._process_guild_notifications(guild)
            except Exception as e:
                logger.error(f"Error processing notifications for guild {guild.id}: {e}")
    
    async def _process_guild_notifications(self, guild: discord.Guild):
        """Process notifications for a single guild.
        
        Args:
            guild: The Discord guild to process notifications for
        """
        logger.info(f"Processing notifications for guild {guild.id} ({guild.name})")
        
        try:
            # Get guild data with caching
            guild_data = await self._get_guild_data(guild.id)
            channel_id = guild_data.get('channels', {}).get('NFL')
            
            # Check if notification channel is set
            if not channel_id:
                logger.debug(f"No notification channel set for guild {guild.id}")
                return
                
            # Get the channel and validate it
            channel = guild.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                logger.warning(f"Invalid notification channel {channel_id} in guild {guild.id}")
                return
            
            # Check bot permissions in the channel
            bot_member = guild.me
            channel_perms = channel.permissions_for(bot_member)
            required_perms = {
                'send_messages': 'Send Messages',
                'embed_links': 'Embed Links',
                'read_messages': 'Read Messages'
            }
            
            # Check for missing permissions
            missing_perms = [
                perm_name for perm, perm_name in required_perms.items()
                if not getattr(channel_perms, perm, False)
            ]
            
            if missing_perms:
                logger.warning(
                    f"Missing permissions in channel {channel.id} for guild {guild.id}: "
                    f"{', '.join(missing_perms)}"
                )
                return
            
            # Process users with notifications enabled
            users_processed = 0
            notifications_sent = 0
            
            for user_id, user_data in guild_data.get('users', {}).items():
                try:
                    # Process user notifications and track results
                    sent = await self._process_user_notifications(user_id, user_data, channel)
                    if sent > 0:
                        users_processed += 1
                        notifications_sent += sent
                        
                except Exception as e:
                    logger.error(f"Error processing user {user_id} in guild {guild.id}: {e}")
            
            # Log summary
            logger.info(
                f"Processed {users_processed} users in guild {guild.id}, "
                f"sent {notifications_sent} notifications"
            )
            
        except Exception as e:
            logger.error(
                f"Error in _process_guild_notifications for guild {guild.id}: {e}",
                exc_info=True
            )
    
    async def _process_user_notifications(self, user_id: str, user_data: Dict, channel: discord.TextChannel) -> int:
        """Process notifications for a single user.
        
        Args:
            user_id: The Discord user ID
            user_data: The user's data from guild settings
            channel: The notification channel to send to
            
        Returns:
            int: Number of notifications sent
        """
        try:
            # Get user's notification settings
            notifications = user_data.get('notifications', {}).get('NFL', {})
            
            # Check if notifications are enabled
            if not notifications.get('enabled', False):
                logger.debug(f"Notifications disabled for user {user_id}")
                return 0
            
            # Get user's team
            team = user_data.get('teams', {}).get('NFL')
            if not team:
                logger.debug(f"No team set for user {user_id}")
                return 0
            
            # Get user's timezone or use default
            timezone_str = notifications.get('timezone', 'America/Los_Angeles')
            try:
                user_tz = pytz.timezone(timezone_str)
            except pytz.exceptions.UnknownTimeZoneError:
                user_tz = pytz.timezone('America/Los_Angeles')
                logger.warning(f"Invalid timezone '{timezone_str}' for user {user_id}, using default")
            
            # Calculate date range in user's timezone
            now = datetime.now(user_tz)
            window_days = min(max(1, int(notifications.get('window_days', DEFAULT_WINDOW_DAYS))), 7)
            end_date = now + timedelta(days=window_days)
            
            logger.debug(
                f"Checking games for {team} in {user_tz.zone} from {now.date()} to {end_date.date()}"
            )
            
            # Get upcoming games
            try:
                games = await self.provider.get_upcoming_games(
                    team=team,
                    start_date=now,
                    end_date=end_date
                )
                logger.debug(f"Found {len(games)} upcoming games for {team}")
            except Exception as e:
                logger.error(f"Error fetching games for {team}: {e}", exc_info=True)
                return 0
            
            # Filter out already notified games
            last_sent = set(notifications.get('last_sent_game_ids', []))
            new_games = [g for g in games if g.game_id and g.game_id not in last_sent]
            
            if not new_games:
                logger.debug(f"No new games to notify user {user_id} about")
                return 0
            
            # Get user mention
            user = self.bot.get_user(int(user_id))
            if not user:
                logger.warning(f"User {user_id} not found in cache")
                return 0
            
            # Send notifications for new games
            notifications_sent = 0
            
            for game in sorted(new_games, key=lambda g: g.start_time_utc):
                try:
                    # Create and send the game notification
                    embed = self._create_game_embed(game, user_tz)
                    
                    # Add team-specific color if available
                    team_colors = {
                        '49ers': 0xAA0000,   # 49ers Red
                        'Chiefs': 0xE31837,   # Chiefs Red
                        'Packers': 0x203731,  # Packers Green
                        # Add more team colors as needed
                    }
                    
                    if embed.color == discord.Color.blue():
                        for team_name, color in team_colors.items():
                            if team_name.lower() in game.home_team.lower() or \
                               team_name.lower() in game.away_team.lower():
                                embed.color = discord.Color(color)
                                break
                    
                    # Send the notification
                    message = f"🔔 {user.mention} - Upcoming {team} game:"
                    await channel.send(message, embed=embed)
                    
                    # Update last sent games
                    last_sent.add(game.game_id)
                    notifications_sent += 1
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.5)
                    
                except discord.HTTPException as e:
                    logger.error(f"Failed to send notification to {user_id}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error sending notification: {e}", exc_info=True)
            
            # Save the updated last_sent list if we sent any notifications
            if notifications_sent > 0:
                try:
                    guild_data = await self._get_guild_data(channel.guild.id)
                    user_data = guild_data['users'].setdefault(user_id, {})
                    nfl_notifications = user_data.setdefault('notifications', {}).setdefault('NFL', {})
                    nfl_notifications['last_sent_game_ids'] = list(last_sent)[-50:]  # Keep last 50 game IDs
                    
                    if not await self._save_guild_data(channel.guild.id, guild_data):
                        logger.error(f"Failed to save last_sent_games for user {user_id}")
                except Exception as e:
                    logger.error(f"Error saving last_sent_games for user {user_id}: {e}")
            
            logger.info(
                f"Sent {notifications_sent} game notifications to user {user_id} "
                f"in guild {channel.guild.id}"
            )
            
            return notifications_sent
            
        except Exception as e:
            logger.error(f"Error in _process_user_notifications for user {user_id}: {e}", exc_info=True)
            return 0
    
    def _create_game_embed(self, game: Game, user_tz: pytz.timezone = None) -> discord.Embed:
        """Create an embed for a game notification.
        
        Args:
            game: The game to create an embed for
            user_tz: The user's timezone (defaults to bot's default)
            
        Returns:
            discord.Embed: The formatted embed
        """
        # Use provided timezone or default
        tz = user_tz or pytz.timezone('America/Los_Angeles')
        
        try:
            # Convert game time to user's timezone
            if game.start_time_utc.tzinfo is None:
                game_time = pytz.utc.localize(game.start_time_utc).astimezone(tz)
            else:
                game_time = game.start_time_utc.astimezone(tz)
            
            # Format the game time
            time_str = discord.utils.format_dt(game_time, 'F')  # Full date/time
            time_relative = discord.utils.format_dt(game_time, 'R')  # Relative time
            
            # Create the embed
            embed = discord.Embed(
                title=f"🏈 {game.away_team} @ {game.home_team}",
                color=discord.Color.blue(),
                timestamp=datetime.now(tz)
            )
            
            # Add game details
            embed.add_field(name="📅 When", value=f"{time_str}\n({time_relative})", inline=True)
            
            if game.venue:
                embed.add_field(name="🏟️ Where", value=game.venue, inline=True)
            
            # Add team records if available
            if hasattr(game, 'away_record') and hasattr(game, 'home_record'):
                embed.add_field(
                    name="📊 Records",
                    value=f"{game.away_team}: {game.away_record}\n{game.home_team}: {game.home_record}",
                    inline=False
                )
            
            # Set thumbnail based on teams (if available)
            team_logos = {
                '49ers': 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/sf.png',
                'Chiefs': 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/kc.png',
                # Add more team logos as needed
            }
            
            for team_name, logo_url in team_logos.items():
                if team_name.lower() in game.home_team.lower() or \
                   team_name.lower() in game.away_team.lower():
                    embed.set_thumbnail(url=logo_url)
                    break
            
            # Add footer with timezone info
            embed.set_footer(
                text=f"Game time is displayed in {tz.zone} time • "
                     f"Use !notify nfl settings to customize"
            )
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating game embed: {e}", exc_info=True)
            # Return a minimal embed if something goes wrong
            return discord.Embed(
                title="🏈 Game Notification",
                description=f"{game.away_team} @ {game.home_team}",
                color=discord.Color.blue()
            )
    
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
        """Enable NFL game notifications.
        
        Example:
            !notify nfl on
        """
        try:
            guild_data = await self._get_guild_data(ctx.guild.id)
            user_data = guild_data['users'].setdefault(str(ctx.author.id), {})
            
            # Check if user has a team set
            team = user_data.get('teams', {}).get('NFL')
            if not team:
                await ctx.send("❌ Please set your favorite NFL team first using `!team set NFL <team>`")
                return
                
            notifications = user_data.setdefault('notifications', {}).setdefault('NFL', {})
            notifications['enabled'] = True
            
            # Set default notification time if not set
            if 'notify_time' not in notifications:
                notifications['notify_time'] = DEFAULT_NOTIFY_TIME.strftime('%H:%M')
            
            if await self._save_guild_data(ctx.guild.id, guild_data):
                # Get notification channel
                channel_id = guild_data.get('channels', {}).get('NFL')
                channel_mention = f"<#{channel_id}>" if channel_id else "a notification channel"
                
                await ctx.send(
                    f"✅ **NFL Notifications Enabled**\n"
                    f"• Team: {team}\n"
                    f"• Time: {notifications['notify_time']} {pytz.timezone('America/Los_Angeles').zone}\n"
                    f"• Channel: {channel_mention if channel_id else 'Not set'}\n\n"
                    f"You'll receive notifications about upcoming {team} games in this server's notification channel. "
                    f"Use `!notify nfl settings` to customize your preferences."
                )
                logger.info(f"Enabled NFL notifications for {ctx.author} (Guild: {ctx.guild.id})")
            else:
                await ctx.send("❌ Failed to save settings. Please try again.")
                
        except Exception as e:
            logger.error(f"Error in nfl_notify_on: {e}", exc_info=True)
            await ctx.send("❌ An error occurred while updating your settings. Please try again later.")
    
    @nfl_notify.command(name="off")
    async def nfl_notify_off(self, ctx):
        """Disable NFL game notifications.
        
        Example:
            !notify nfl off
        """
        try:
            guild_data = await self._get_guild_data(ctx.guild.id)
            user_data = guild_data['users'].setdefault(str(ctx.author.id), {})
            notifications = user_data.setdefault('notifications', {}).setdefault('NFL', {})
            
            if not notifications.get('enabled', False):
                await ctx.send("ℹ️ NFL game notifications are already disabled.")
                return
                
            notifications['enabled'] = False
            
            if await self._save_guild_data(ctx.guild.id, guild_data):
                team = user_data.get('teams', {}).get('NFL', 'your team')
                await ctx.send(
                    f"🔕 **NFL Notifications Disabled**\n"
                    f"You will no longer receive notifications for {team} games in this server.\n"
                    f"Use `!notify nfl on` to re-enable them at any time."
                )
                logger.info(f"Disabled NFL notifications for {ctx.author} (Guild: {ctx.guild.id})")
            else:
                await ctx.send("❌ Failed to save settings. Please try again.")
                
        except Exception as e:
            logger.error(f"Error in nfl_notify_off: {e}", exc_info=True)
            await ctx.send("❌ An error occurred while updating your settings. Please try again later.")
    
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
        now = datetime.now(pytz.timezone('America/Los_Angeles'))
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
