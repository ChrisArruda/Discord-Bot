import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "!"

# File paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Game configuration
VALID_LEAGUES = {
    "NFL": ["Bills", "Cardinals", "Ravens", "Falcons", "Panthers", "Bengals", "Bears", "Browns", 
             "Cowboys", "Broncos", "Lions", "Texans", "Packers", "Colts", "Rams", "Jaguars", 
             "Vikings", "Chiefs", "Saints", "Raiders", "Giants", "Chargers", "Eagles", "Dolphins", 
             "49ers", "Patriots", "Seahawks", "Jets", "Buccaneers", "Steelers", "Commanders", "Titans"],
    "NBA": ["Clippers", "Celtics", "Nets", "Knicks", "76ers", "Raptors", "Bulls", "Cavaliers", 
            "Pistons", "Pacers", "Bucks", "Hawks", "Hornets", "Heat", "Magic", "Wizards", "Nuggets", 
            "Timberwolves", "Thunder", "Blazers", "Jazz", "Warriors", "Lakers", "Suns", "Kings", 
            "Mavericks", "Rockets", "Grizzlies", "Pelicans", "Spurs"],
    "NHL": ["Kings", "Hurricanes", "Bruins", "Jackets", "Sabres", "Devils", "Wings", "Islanders", 
            "Panthers", "Rangers", "Canadiens", "Flyers", "Senators", "Penguins", "Lightning", 
            "Capitals", "Leafs", "Blackhawks", "Ducks", "Avalanche", "Flames", "Stars", "Oilers", 
            "Wild", "Predators", "Sharks", "Blues", "Kraken", "Utah", "Canucks", "Jets", "Knights"]
}

# Default user profile
default_user_profile = {
    "birthday": {"month": 0, "day": 0},
    "pronouns": "",
    "anime": [],
    "teams": {},
    "tictactoe_stats": {"wins": 0, "losses": 0, "draws": 0},
    "rps_stats": {"wins": 0, "losses": 0, "draws": 0},
    "notifications": {
        "enabled": True,
        "timezone": "UTC",
        "notify_before_game": 60,  # minutes before game
        "notify_game_start": True,
        "notify_scores": True,
        "notify_final_score": True
    }
}
