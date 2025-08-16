import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
from typing import Optional
import logging

from ..utils.database import db

logger = logging.getLogger(__name__)

class Profile(commands.Cog):
    """Commands for managing user profiles."""
    
    def __init__(self, bot):
        self.bot = bot
        self.birthday_check.start()
        
    def cog_unload(self):
        self.birthday_check.cancel()
    
    @commands.hybrid_command(name="set_birthday", description="Set your birthday (MM DD)")
    async def set_birthday(self, ctx, month: int, day: int):
        """Set your birthday (MM DD)."""
        if not (1 <= month <= 12 and 1 <= day <= 31):
            await ctx.send("⚠️ Invalid date! Format: `!set_birthday MM DD`.", ephemeral=True)
            return
            
        db.update_user_data(ctx.guild.id, ctx.author.id, birthday={"month": month, "day": day})
        await ctx.send(f"🎉 {ctx.author.mention}, your birthday is set to **{month}/{day}**!")
    
    @commands.hybrid_command(name="remove_birthday", description="Remove your stored birthday")
    async def remove_birthday(self, ctx):
        """Remove your stored birthday."""
        user_data = db.ensure_user_profile(ctx.guild.id, ctx.author.id)
        if user_data["birthday"]["month"] == 0 and user_data["birthday"]["day"] == 0:
            await ctx.send(f"⚠️ {ctx.author.mention}, you don't have a birthday set!", ephemeral=True)
            return
            
        db.update_user_data(ctx.guild.id, ctx.author.id, birthday={"month": 0, "day": 0})
        await ctx.send(f"✅ {ctx.author.mention}, your birthday has been removed!")
    
    @commands.hybrid_command(name="set_pronouns", description="Set your pronouns")
    async def set_pronouns(self, ctx, *, pronouns: str):
        """Set your pronouns (e.g., she/her, he/him, they/them)."""
        allowed = ["he", "him", "she", "her", "they", "them"]
        parts = [p.lower() for p in pronouns.replace("/", " ").split()]

        if not all(p in allowed for p in parts):
            await ctx.send(
                "⚠️ Invalid pronouns! Allowed options: he/him, she/her, they/them, he/they, etc.",
                ephemeral=True
            )
            return
            
        pronouns_str = " / ".join(parts)
        db.update_user_data(ctx.guild.id, ctx.author.id, pronouns=pronouns_str)
        await ctx.send(f"✅ {ctx.author.mention}, your pronouns have been set to **{pronouns_str}**!")
    
    @commands.hybrid_command(name="profile", description="View your or another user's profile")
    async def profile(self, ctx, member: Optional[discord.Member] = None):
        """View your or another user's profile."""
        member = member or ctx.author
        user_data = db.ensure_user_profile(ctx.guild.id, member.id)
        
        # Format profile data
        birthday = user_data["birthday"]
        birthday_str = f"{birthday['month']}/{birthday['day']}" if birthday["month"] > 0 else "Not set"
        pronouns = user_data.get("pronouns", "Not set")
        
        # Format teams
        teams = user_data.get("teams", {})
        teams_str = "\n".join(f"{league}: **{team}**" for league, team in teams.items()) or "None set"
        
        # Create embed
        embed = discord.Embed(title=f"{member.display_name}'s Profile", color=discord.Color.purple())
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add fields
        embed.add_field(name="🎂 Birthday", value=birthday_str, inline=True)
        embed.add_field(name="📛 Pronouns", value=pronouns, inline=True)
        embed.add_field(name="🏈 Favorite Teams", value=teams_str, inline=False)
        
        # Add game stats if available
        if "tictactoe_stats" in user_data:
            ttt = user_data["tictactoe_stats"]
            embed.add_field(
                name="🎮 Tic-Tac-Toe", 
                value=f"{ttt['wins']}W - {ttt['losses']}L - {ttt['draws']}D",
                inline=True
            )
            
        if "rps_stats" in user_data:
            rps = user_data["rps_stats"]
            embed.add_field(
                name="🪨 Rock-Paper-Scissors",
                value=f"{rps['wins']}W - {rps['losses']}L - {rps['draws']}D",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @tasks.loop(hours=24)
    async def birthday_check(self):
        """Check for birthdays and send announcements."""
        today = datetime.utcnow()
        today_str = today.strftime("%Y-%m-%d")
        
        # For each guild the bot is in
        for guild in self.bot.guilds:
            data = db.load_server_data(guild.id)
            updated = False
            
            for user_id, user_data in data.items():
                # Skip if not a valid user ID or no birthday set
                if not user_id.isdigit() or "birthday" not in user_data:
                    continue
                    
                birthday = user_data["birthday"]
                if (birthday.get("month") == today.month and 
                    birthday.get("day") == today.day and
                    user_data.get("last_birthday_check") != today_str):
                    
                    # Update last checked date
                    user_data["last_birthday_check"] = today_str
                    updated = True
                    
                    # Send birthday message
                    channel = discord.utils.get(guild.text_channels, name="💬general")
                    if channel:
                        try:
                            member = guild.get_member(int(user_id))
                            if member:
                                await channel.send(f"🎉 @everyone Happy Birthday, {member.mention}! 🎂🎁")
                        except Exception as e:
                            print(f"Error sending birthday message: {e}")
            
            # Save updates if any
            if updated:
                db.save_server_data(guild.id, data)
    
    @birthday_check.before_loop
    async def before_birthday_check(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Profile(bot))
