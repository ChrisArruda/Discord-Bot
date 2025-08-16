import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from discord.ext import commands
from ..config import DATA_DIR, default_user_profile

class Database:
    """Handles all data storage and retrieval for the bot."""
    
    def __init__(self):
        self.data_dir = DATA_DIR
        
    def get_server_file(self, guild_id: int) -> Path:
        """Get the path to a server's data file."""
        return self.data_dir / f"{guild_id}.json"
    
    def load_server_data(self, guild_id: int) -> Dict[str, Any]:
        """Load data for a server."""
        server_file = self.get_server_file(guild_id)
        try:
            if server_file.exists():
                with open(server_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return {}
    
    def save_server_data(self, guild_id: int, data: Dict[str, Any]) -> None:
        """Save data for a server."""
        server_file = self.get_server_file(guild_id)
        try:
            with open(server_file, 'w') as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            print(f"Error saving server data: {e}")
    
    def ensure_user_profile(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Ensure a user has a profile, creating one if needed."""
        data = self.load_server_data(guild_id)
        user_id_str = str(user_id)
        
        if user_id_str not in data:
            data[user_id_str] = default_user_profile.copy()
            self.save_server_data(guild_id, data)
        
        # Migrate old format if needed
        user_data = data[user_id_str]
        if "month" in user_data and "day" in user_data:
            user_data["birthday"] = {
                "month": user_data.pop("month"),
                "day": user_data.pop("day")
            }
            self.save_server_data(guild_id, data)
            
        return data[user_id_str]
    
    def update_user_data(self, guild_id: int, user_id: int, **updates) -> Dict[str, Any]:
        """Update user data with the provided fields."""
        data = self.load_server_data(guild_id)
        user_id_str = str(user_id)
        
        if user_id_str not in data:
            data[user_id_str] = default_user_profile.copy()
            
        data[user_id_str].update(updates)
        self.save_server_data(guild_id, data)
        return data[user_id_str]
    
    def get_all_users(self, guild_id: int) -> dict:
        """Get all users for a specific server.
        
        Args:
            guild_id: The ID of the server
            
        Returns:
            dict: A dictionary of user data for the server
        """
        data = self.load_server_data(guild_id)
        # Filter out non-user entries (like '_meta')
        return {k: v for k, v in data.items() if k.isdigit()}

# Global database instance
db = Database()
