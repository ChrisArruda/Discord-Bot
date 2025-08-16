# Discord Bot

A feature-rich Discord bot with games, user profiles, and more!

## Features

- 🎮 **Games**: Play Tic-Tac-Toe and Rock-Paper-Scissors (LOTR Edition)
- 👤 **User Profiles**: Set your pronouns, birthday, and favorite teams
- 🎂 **Birthday Announcements**: Automatic birthday announcements
- 🏆 **Stats Tracking**: Track your game statistics

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd discord-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root with your Discord bot token:
   ```
   DISCORD_TOKEN=your_bot_token_here
   ```

4. **Run the bot**
   ```bash
   python run.py
   ```
   
   Or alternatively:
   ```bash
   python -m discord_bot.bot
   ```

## Commands

### Profile Commands
- `!profile [@user]` - View your or another user's profile
- `!set_birthday <MM> <DD>` - Set your birthday
- `!remove_birthday` - Remove your birthday
- `!set_pronouns <pronouns>` - Set your pronouns (e.g., he/him, she/her, they/them)

### Team Commands
- `!set_team <league> <team>` - Set your favorite team
- `!teams [league]` - List all teams in a league
- `!my_teams [@user]` - View your or another user's favorite teams

### Game Commands
- `!tictactoe` - Start a new Tic-Tac-Toe game
- `!move <1-9>` - Make a move in Tic-Tac-Toe
- `!rps <orc|hobbit|elf>` - Play Rock-Paper-Scissors (LOTR Edition)

## Project Structure

```
discord_bot/
├── cogs/               # Command groups
│   ├── games.py       # Game commands
│   ├── profile.py     # Profile commands
│   └── teams.py       # Team management
├── utils/             # Utility functions
│   ├── database.py    # Database operations
│   └── helpers.py     # Helper functions
├── __init__.py
├── bot.py            # Main bot file
└── config.py         # Configuration
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
