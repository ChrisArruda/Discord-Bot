import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import tempfile
import atexit

logger = logging.getLogger(__name__)

class JsonStore:
    """Thread-safe JSON file storage with atomic writes."""
    
    _instance = None
    _locks: Dict[str, asyncio.Lock] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            atexit.register(cls.cleanup)
        return cls._instance
    
    @classmethod
    def cleanup(cls):
        """Clean up any remaining locks on exit."""
        for lock in cls._locks.values():
            if lock.locked():
                lock.release()
    
    def _get_lock(self, filepath: str) -> asyncio.Lock:
        """Get or create a lock for a file path."""
        if filepath not in self._locks:
            self._locks[filepath] = asyncio.Lock()
        return self._locks[filepath]
    
    async def read(self, filepath: str, default: Optional[Dict] = None) -> Dict:
        """Read JSON data from a file with a lock."""
        path = Path(filepath)
        lock = self._get_lock(str(path.absolute()))
        
        async with lock:
            try:
                if not path.exists():
                    return default or {}
                
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
                    
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Error reading {path}: {e}")
                return default or {}
    
    async def write(self, filepath: str, data: Dict) -> bool:
        """Write JSON data to a file atomically with a lock."""
        path = Path(filepath)
        lock = self._get_lock(str(path.absolute()))
        temp_path = None
        
        async with lock:
            try:
                # Create parent directories if they don't exist
                path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write to a temporary file first
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    dir=str(path.parent),
                    prefix=f"{path.name}.",
                    suffix='.tmp',
                    delete=False
                ) as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    temp_path = f.name
                
                # On Windows, we need to remove the destination first
                try:
                    if path.exists():
                        path.unlink()
                except OSError:
                    pass
                
                # Atomic rename
                os.replace(temp_path, path)
                return True
                
            except (OSError, json.JSONEncodeError) as e:
                logger.error(f"Error writing to {path}: {e}")
                try:
                    if temp_path and os.path.exists(temp_path):
                        os.unlink(temp_path)
                except (NameError, OSError):
                    pass
                return False

# Global instance
json_store = JsonStore()
