from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Protocol
import aiohttp
import hashlib
import json
import logging
from functools import lru_cache
import time

logger = logging.getLogger(__name__)

@dataclass
class Game:
    """Represents a sports game with teams and timing information."""
    home_team: str
    away_team: str
    start_time_utc: datetime
    venue: Optional[str] = None
    league: str = "NFL"
    game_id: Optional[str] = None
    
    def __post_init__(self):
        # Ensure start_time_utc is timezone-aware
        if self.start_time_utc.tzinfo is None:
            self.start_time_utc = self.start_time_utc.replace(tzinfo=timezone.utc)
        elif self.start_time_utc.tzinfo != timezone.utc:
            self.start_time_utc = self.start_time_utc.astimezone(timezone.utc)
    
    def to_dict(self) -> Dict:
        """Convert game to a dictionary for JSON serialization."""
        data = asdict(self)
        data['start_time_utc'] = self.start_time_utc.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Game':
        """Create a Game from a dictionary."""
        data = data.copy()
        data['start_time_utc'] = datetime.fromisoformat(data['start_time_utc'])
        return cls(**data)

class ScheduleProvider(Protocol):
    """Protocol for schedule providers."""
    
    async def get_upcoming_games(self, team: str, start_date: datetime, end_date: datetime) -> List[Game]:
        """Get upcoming games for a team within a date range."""
        ...

class EspnNflProvider:
    """ESPN NFL schedule provider with caching."""
    
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
    CACHE_TTL = 24 * 60 * 60  # 24 hours
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self._cache: Dict[str, tuple[float, List[Game]]] = {}
    
    def _get_cache_key(self, team: str, start_date: datetime, end_date: datetime) -> str:
        """Generate a cache key for the query."""
        return f"{team}:{start_date.date()}:{end_date.date()}"
    
    def _clean_cache(self):
        """Remove expired cache entries."""
        now = time.time()
        self._cache = {
            k: v for k, v in self._cache.items() 
            if now - v[0] < self.CACHE_TTL
        }
    
    async def get_upcoming_games(self, team: str, start_date: datetime, end_date: datetime) -> List[Game]:
        """Get upcoming games with caching."""
        cache_key = self._get_cache_key(team, start_date, end_date)
        self._clean_cache()
        
        if cache_key in self._cache:
            return self._cache[cache_key][1]
        
        try:
            # First try to get team schedule
            team_id = await self._get_team_id(team)
            if not team_id:
                return []
                
            url = f"{self.BASE_URL}/teams/{team_id}/schedule"
            params = {
                "dates": f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}",
                "seasontype": "2"  # Regular season
            }
            
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                data = await response.json()
                
            games = self._parse_games(data.get('events', []))
            self._cache[cache_key] = (time.time(), games)
            return games
            
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.error(f"Error fetching schedule: {e}")
            return []
    
    async def _get_team_id(self, team_name: str) -> Optional[str]:
        """Get ESPN team ID from team name."""
        team_mapping = {
            # NFC Teams
            'cardinals': 'ari', 'falcons': 'atl', 'ravens': 'bal', 'bills': 'buf', 'panthers': 'car',
            'bears': 'chi', 'bengals': 'cin', 'browns': 'cle', 'cowboys': 'dal', 'broncos': 'den',
            'lions': 'det', 'packers': 'gb', 'texans': 'hou', 'colts': 'ind', 'jaguars': 'jac',
            'chiefs': 'kc', 'raiders': 'lv', 'chargers': 'lac', 'rams': 'la', 'dolphins': 'mia',
            'vikings': 'min', 'patriots': 'ne', 'saints': 'no', 'giants': 'nyg', 'jets': 'nyj',
            'eagles': 'phi', 'steelers': 'pit', '49ers': 'sf', 'seahawks': 'sea', 'buccaneers': 'tb',
            'titans': 'ten', 'commanders': 'was',
            
            # Common alternate names
            'sf 49ers': 'sf', 'san francisco': 'sf', 'san fran': 'sf',
            'new england': 'ne', 'new orleans': 'no', 'tampa bay': 'tb',
            'kansas city': 'kc', 'green bay': 'gb', 'las vegas': 'lv'
        }
        return team_mapping.get(team_name.lower())
    
    def _parse_games(self, events: List[Dict]) -> List[Game]:
        """Parse games from ESPN API response."""
        games = []
        for event in events:
            try:
                competitions = event.get('competitions', [{}])[0]
                competitors = {
                    comp.get('homeAway'): comp.get('team', {}).get('displayName')
                    for comp in competitions.get('competitors', [])
                }
                
                game = Game(
                    home_team=competitors.get('home', 'TBD'),
                    away_team=competitors.get('away', 'TBD'),
                    start_time_utc=datetime.fromisoformat(event['date'].replace('Z', '+00:00')),
                    venue=competitions.get('venue', {}).get('fullName'),
                    game_id=event.get('id')
                )
                games.append(game)
            except (KeyError, ValueError) as e:
                logger.warning(f"Error parsing game: {e}")
                continue
        return games

class MockNflProvider:
    """Mock provider for testing with sample data."""
    
    def __init__(self, sample_data: List[Dict] = None):
        self.sample_data = sample_data or []
    
    async def get_upcoming_games(self, team: str, start_date: datetime, end_date: datetime) -> List[Game]:
        """Get mock games for testing."""
        return [
            Game.from_dict(game) for game in self.sample_data
            if game.get('league') == 'NFL' and 
               start_date <= datetime.fromisoformat(game['start_time_utc']) <= end_date
        ]
