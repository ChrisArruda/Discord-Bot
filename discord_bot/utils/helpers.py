from typing import Any, Dict, Optional
import discord
from datetime import datetime

def format_dt(dt: datetime, style: Optional[str] = None) -> str:
    """Convert a datetime into a Discord timestamp."""
    valid_styles = ['t', 'T', 'd', 'D', 'f', 'F', 'R']
    if style and style not in valid_styles:
        style = None
    return f"<t:{int(dt.timestamp())}{f':{style}' if style else ''}>`"

def create_embed(
    title: str = "",
    description: str = "",
    color: Optional[discord.Color] = None,
    **kwargs
) -> discord.Embed:
    """Create a Discord embed with common defaults."""
    if color is None:
        color = discord.Color.blue()
    
    embed = discord.Embed(title=title, description=description, color=color)
    
    # Handle additional kwargs that might be passed
    if 'timestamp' in kwargs:
        embed.timestamp = kwargs['timestamp']
    if 'url' in kwargs:
        embed.url = kwargs['url']
    if 'footer' in kwargs:
        if isinstance(kwargs['footer'], str):
            embed.set_footer(text=kwargs['footer'])
        elif isinstance(kwargs['footer'], dict):
            embed.set_footer(**kwargs['footer'])
    if 'image' in kwargs:
        embed.set_image(url=kwargs['image'])
    if 'thumbnail' in kwargs:
        embed.set_thumbnail(url=kwargs['thumbnail'])
    if 'author' in kwargs:
        if isinstance(kwargs['author'], str):
            embed.set_author(name=kwargs['author'])
        elif isinstance(kwargs['author'], dict):
            embed.set_author(**kwargs['author'])
    
    # Handle fields if provided as a list of (name, value, inline) tuples
    if 'fields' in kwargs and isinstance(kwargs['fields'], list):
        for field in kwargs['fields']:
            if len(field) == 2:
                name, value = field
                inline = False
            else:
                name, value, inline = field
            embed.add_field(name=name, value=value, inline=inline)
    
    return embed

def format_user(user: discord.User) -> str:
    """Format a user mention with their name and discriminator."""
    return f"{user.mention} (`{user}`)"

def format_duration(seconds: int) -> str:
    """Format a duration in seconds to a human-readable string."""
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 and days == 0:  # Only show minutes if < 1 day
        parts.append(f"{minutes}m")
    if seconds > 0 and hours == 0 and days == 0:  # Only show seconds if < 1 hour
        parts.append(f"{seconds}s")
    
    return " ".join(parts) if parts else "0s"

def get_embed_color(level: str = "info") -> discord.Color:
    """Get a color based on the message level."""
    colors = {
        "success": discord.Color.green(),
        "error": discord.Color.red(),
        "warning": discord.Color.gold(),
        "info": discord.Color.blue(),
        "debug": discord.Color.light_grey(),
    }
    return colors.get(level.lower(), discord.Color.blue())

def paginate(text: str, max_length: int = 2000, delimiter: str = "\n") -> list:
    """Split text into chunks that are each under max_length, respecting line breaks."""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for line in text.split(delimiter):
        if len(current_chunk) + len(line) + len(delimiter) > max_length and current_chunk:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += delimiter + line
            else:
                current_chunk = line
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks
