import json
import shutil
from pathlib import Path

# Define paths
BASE_DIR = Path(__file__).parent
MAIN_JSON = BASE_DIR / "795899460794318859.json"
DATA_JSON = BASE_DIR / "data" / "795899460794318859.json"
GUILDS_JSON = BASE_DIR / "data" / "guilds" / "795899460794318859.json"
BACKUP_DIR = BASE_DIR / "backups"

# Create backup directory
BACKUP_DIR.mkdir(exist_ok=True, parents=True)

# Backup existing files
print("Creating backups...")
shutil.copy2(MAIN_JSON, BACKUP_DIR / "main_795899460794318859.json.bak")
if DATA_JSON.exists():
    shutil.copy2(DATA_JSON, BACKUP_DIR / "data_795899460794318859.json.bak")
shutil.copy2(GUILDS_JSON, BACKUP_DIR / "guilds_795899460794318859.json.bak")

# Load data
print("Loading data...")
with open(MAIN_JSON, 'r') as f:
    main_data = json.load(f)

with open(GUILDS_JSON, 'r') as f:
    guild_data = json.load(f)

# Create new structure
new_data = {
    "guild_id": guild_data.get("guild_id", "795899460794318859"),
    "channels": guild_data.get("channels", {"NFL": None}),
    "users": main_data  # This contains all user data
}

# Save merged data
print("Saving merged data...")
with open(GUILDS_JSON, 'w') as f:
    json.dump(new_data, f, indent=4)

# Remove old files (after successful merge)
print("Cleaning up...")
if MAIN_JSON.exists():
    MAIN_JSON.unlink()
if DATA_JSON.exists():
    DATA_JSON.unlink()

print("Merge complete! Backups saved to:", BACKUP_DIR.absolute())
