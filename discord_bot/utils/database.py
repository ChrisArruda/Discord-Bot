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
        self.guilds_dir = DATA_DIR / "guilds"
        self.guilds_dir.mkdir(exist_ok=True, parents=True)
        
    def get_server_file(self, guild_id: int) -> Path:
        """Get the path to a server's data file.
        
        Args:
            guild_id: The ID of the server
            
        Returns:
            Path: Path to the server's data file
        """
        return self.guilds_dir / f"{guild_id}.json"
    
    def load_server_data(self, guild_id: int) -> Dict[str, Any]:
        """Load data for a server.
        
        Args:
            guild_id: The ID of the server
            
        Returns:
            dict: The server's data
        """
        server_file = self.get_server_file(guild_id)
        try:
            if server_file.exists():
                with open(server_file, 'r') as f:
                    data = json.load(f)
                    # If this is an old-format file (no guild_id at top level),
                    # convert it to the new format
                    if not isinstance(data, dict) or 'guild_id' not in data:
                        data = {
                            'guild_id': str(guild_id),
                            'channels': {'NFL': None},
                            'users': data or {}
                        }
                        self.save_server_data(guild_id, data)
                    return data
            return {'guild_id': str(guild_id), 'channels': {'NFL': None}, 'users': {}}
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading server data for guild {guild_id}: {e}")
            return {'guild_id': str(guild_id), 'channels': {'NFL': None}, 'users': {}}
    
    def save_server_data(self, guild_id: int, data: Dict[str, Any]) -> bool:
        """Save data for a server.
        
        Args:
            guild_id: The ID of the server
            data: The data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        server_file = self.get_server_file(guild_id)
        try:
            with open(server_file, 'w') as f:
                json.dump(data, f, indent=4, sort_keys=True)
            return True
        except IOError as e:
            print(f"Error saving server data for guild {guild_id}: {e}")
            return False
    
    def ensure_user_profile(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """Ensure a user has a profile, creating one if needed.
        
        Args:
            guild_id: The ID of the server
            user_id: The ID of the user
            
        Returns:
            dict: The user's profile data
        """
        data = self.load_server_data(guild_id)
        user_id_str = str(user_id)
        
        # Initialize users dictionary if it doesn't exist
        if 'users' not in data:
            data['users'] = {}
        
        if user_id_str not in data['users']:
            data['users'][user_id_str] = default_user_profile.copy()
            self.save_server_data(guild_id, data)
        
        # Migrate old format if needed
        user_data = data['users'][user_id_str]
        if not isinstance(user_data, dict):
            user_data = {}
            data['users'][user_id_str] = user_data
            self.save_server_data(guild_id, data)
        
        # Ensure all default fields exist
        updated = False
        for key, default_value in default_user_profile.items():
            if key not in user_data:
                user_data[key] = default_value
                updated = True
        
        if updated:
            self.save_server_data(guild_id, data)
            
        return user_data
    
    def update_user_data(self, guild_id: int, user_id: int, **updates) -> Dict[str, Any]:
        """Update user data with the provided fields.
        
        Args:
            guild_id: The ID of the server
            user_id: The ID of the user
            **updates: Key-value pairs to update
            
        Returns:
            dict: The updated user data
        """
        data = self.load_server_data(guild_id)
        user_id_str = str(user_id)
        
        # Ensure users dictionary exists
        if 'users' not in data:
            data['users'] = {}
        
        # Ensure user exists
        if user_id_str not in data['users']:
            data['users'][user_id_str] = default_user_profile.copy()
        
        # Update user data
        data['users'][user_id_str].update(updates)
        
        # Save changes
        if self.save_server_data(guild_id, data):
            return data['users'][user_id_str]
        return {}
    
    def get_all_users(self, guild_id: int) -> dict:
        """Get all users for a specific server.
        
        Args:
            guild_id: The ID of the server
            
        Returns:
            dict: A dictionary of user data for the server
        """
        data = self.load_server_data(guild_id)
        users = data.get('users', {})
        # Filter out non-user entries (like '_meta')
        return {k: v for k, v in users.items() if k.isdigit()}

# Global database instance
db = Database()
