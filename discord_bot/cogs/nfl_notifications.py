{{ ... }}
class NFLNotifications(commands.Cog):
    """Handles NFL game notifications for users."""
    
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.nfl_teams = {team.lower(): team for team in VALID_LEAGUES["NFL"]}
        self.cache_file = DATA_DIR / "nfl_cache.json"
        self.cache = self._load_cache()
        self.rate_limit_remaining = 100  # Default value, will be updated from headers
        self.rate_limit_reset = 0  # Timestamp when rate limit resets
        self.rate_limit_lock = asyncio.Lock()
        self.check_games.start()
    
    async def _make_api_request(self, url: str) -> Optional[Dict]:
        """Make an API request with rate limiting and error handling."""
        headers = {
            'User-Agent': 'DiscordBot/1.0 (https://your-bot-url.com)'
        }
        
        async with self.rate_limit_lock:
            # Check if we're rate limited
            current_time = time.time()
            if self.rate_limit_remaining <= 0 and current_time < self.rate_limit_reset:
                wait_time = int(self.rate_limit_reset - current_time) + 1
                logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            
            # Make the request
            try:
                async with self.session.get(url, headers=headers) as response:
                    # Update rate limit info from headers
                    if 'X-RateLimit-Remaining' in response.headers:
                        self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
                    if 'X-RateLimit-Reset' in response.headers:
                        self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
                    
                    # Handle rate limit errors
                    if response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limited. Retrying after {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        return await self._make_api_request(url)  # Retry the request
                    
                    # Handle other errors
                    response.raise_for_status()
                    
                    # Return JSON response
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                logger.error(f"API request failed: {e}")
                # Exponential backoff for retries
                await asyncio.sleep(5)  # Wait before retrying
                try:
                    return await self._make_api_request(url)
                except Exception as retry_error:
                    logger.error(f"Retry failed: {retry_error}")
                    return None
            
            except Exception as e:
                logger.error(f"Unexpected error in API request: {e}")
                return None
    
    async def get_upcoming_games(self) -> List[Dict]:
        """Fetch upcoming NFL games from the API with rate limiting."""
        url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
        data = await self._make_api_request(url)
        return data.get("events", []) if data else []
    
    async def get_team_schedule(self, team_name: str) -> List[Dict]:
        """Get the schedule for a specific team with rate limiting."""
        team_name = TEAM_NAME_MAPPING.get(team_name, team_name)
        team_id = REVERSE_TEAM_MAPPING.get(team_name)
        
        if not team_id:
            logger.error(f"Could not find team ID for {team_name}")
            return []
            
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/schedule"
        data = await self._make_api_request(url)
        return data.get("events", []) if data else []
{{ ... }}
