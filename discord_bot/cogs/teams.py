import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import pytz

from ..config import VALID_LEAGUES
from ..utils.database import db

class Teams(commands.Cog):
    """Commands for managing favorite teams."""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="set_team", description="Set your favorite team in a league")
    async def set_team(self, ctx, league: str, *, team: str):
        """Set your favorite team in a league.
        
        Example: !set_team NFL "San Francisco 49ers"
        """
        league = league.upper()
        team = team.title()
        
        # Validate league and team
        if league not in VALID_LEAGUES:
            valid_leagues = ", ".join(VALID_LEAGUES.keys())
            await ctx.send(
                f"⚠️ Invalid league! Available leagues: {valid_leagues}",
                ephemeral=True
            )
            return
            
        if team not in VALID_LEAGUES[league]:
            await ctx.send(
                f"⚠️ Invalid team for {league}! Please check the team name and try again.",
                ephemeral=True
            )
            return
        
        # Update user's team
        user_data = db.ensure_user_profile(ctx.guild.id, ctx.author.id)
        user_data.setdefault("teams", {})[league] = team
        db.save_server_data(ctx.guild.id, {str(ctx.author.id): user_data})
        
        await ctx.send(
            f"✅ {ctx.author.mention}, your favorite **{league}** team is now **{team}**!"
        )
    
    @commands.hybrid_command(name="teams", description="List all valid teams in a league")
    async def list_teams(self, ctx, league: Optional[str] = None):
        """List all valid teams in a league."""
        if league:
            league = league.upper()
            if league not in VALID_LEAGUES:
                valid_leagues = ", ".join(VALID_LEAGUES.keys())
                await ctx.send(
                    f"⚠️ Invalid league! Available leagues: {valid_leagues}",
                    ephemeral=True
                )
                return
            
            # List teams for specific league
            teams = sorted(VALID_LEAGUES[league])
            teams_chunks = [teams[i:i + 10] for i in range(0, len(teams), 10)]
            
            for i, chunk in enumerate(teams_chunks):
                embed = discord.Embed(
                    title=f"{league} Teams" + (f" (Page {i+1})" if len(teams_chunks) > 1 else ""),
                    color=discord.Color.blue()
                )
                embed.description = "\n".join(f"• {team}" for team in chunk)
                await ctx.send(embed=embed)
        else:
            # List all available leagues
            embed = discord.Embed(
                title="Available Leagues",
                description="Use `!teams <league>` to see teams in a specific league.",
                color=discord.Color.blue()
            )
            
            for league_name, teams in VALID_LEAGUES.items():
                embed.add_field(
                    name=league_name,
                    value=f"{len(teams)} teams available",
                    inline=True
                )
            
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="my_teams", description="Show your favorite teams")
    async def my_teams(self, ctx, member: Optional[discord.Member] = None):
        """Show your or another user's favorite teams."""
        member = member or ctx.author
        user_data = db.ensure_user_profile(ctx.guild.id, member.id)
        
        teams = user_data.get("teams", {})
        
        if not teams:
            await ctx.send(
                f"ℹ️ {member.display_name} hasn't set any favorite teams yet!",
                ephemeral=member != ctx.author
            )
            return
        
        embed = discord.Embed(
            title=f"{member.display_name}'s Favorite Teams",
            color=discord.Color.green()
        )
        
        for league, team in teams.items():
            embed.add_field(name=league, value=team, inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="notify_settings", description="Configure your game notification settings")
    async def notification_settings(
        self,
        ctx,
        enabled: Optional[bool] = None,
        timezone: Optional[str] = None,
        notify_before: Optional[int] = None,
        notify_start: Optional[bool] = None,
        notify_scores: Optional[bool] = None,
        notify_final: Optional[bool] = None
    ):
        """Configure your game notification settings.
        
        Parameters:
        enabled: Enable/disable all notifications
        timezone: Your timezone (e.g., 'America/New_York')
        notify_before: Minutes before game to notify (0-1440)
        notify_start: Notify when game starts
        notify_scores: Notify for score updates
        notify_final: Notify for final score
        """
        updates = {}
        
        if enabled is not None:
            updates["notifications.enabled"] = enabled
        
        if timezone and timezone in pytz.all_timezones:
            updates["notifications.timezone"] = timezone
        elif timezone:
            await ctx.send(f"⚠️ Invalid timezone. Use one from: https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568", ephemeral=True)
            return
        
        if notify_before is not None:
            if 0 <= notify_before <= 1440:
                updates["notifications.notify_before_game"] = notify_before
            else:
                await ctx.send("⚠️ Notification time must be between 0 and 1440 minutes.", ephemeral=True)
                return
        
        if notify_start is not None:
            updates["notifications.notify_game_start"] = notify_start
        
        if notify_scores is not None:
            updates["notifications.notify_scores"] = notify_scores
        
        if notify_final is not None:
            updates["notifications.notify_final_score"] = notify_final
        
        if not updates:
            # Show current settings if no updates provided
            user_data = db.ensure_user_profile(ctx.guild.id, ctx.author.id)
            notif_settings = user_data.get("notifications", {})
            
            embed = discord.Embed(
                title="🔔 Notification Settings",
                description="Current notification preferences:",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Notifications Enabled", value=notif_settings.get("enabled", True), inline=True)
            embed.add_field(name="Timezone", value=notif_settings.get("timezone", "UTC"), inline=True)
            embed.add_field(name="Notify Before Game (min)", 
                          value=str(notif_settings.get("notify_before_game", 60)), 
                          inline=True)
            embed.add_field(name="Notify on Game Start", 
                          value=notif_settings.get("notify_game_start", True), 
                          inline=True)
            embed.add_field(name="Notify Score Updates", 
                          value=notif_settings.get("notify_scores", True), 
                          inline=True)
            embed.add_field(name="Notify Final Score", 
                          value=notif_settings.get("notify_final_score", True), 
                          inline=True)
            
            embed.set_footer(text=f"Use {ctx.prefix}notify_settings [options] to change settings")
            
            await ctx.send(embed=embed)
            return
        
        # Update user preferences
        user_data = db.ensure_user_profile(ctx.guild.id, ctx.author.id)
        
        # Handle nested updates
        for key, value in updates.items():
            if '.' in key:
                # Handle nested keys (e.g., "notifications.enabled")
                parts = key.split('.')
                current = user_data
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                user_data[key] = value
        
        db.save_server_data(ctx.guild.id, {str(ctx.author.id): user_data})
        await ctx.send("✅ Notification settings updated!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Teams(bot))
