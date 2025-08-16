# bot.py
import os
import json
import discord
import random
from dotenv import load_dotenv
from discord.ext import commands, tasks
from datetime import datetime

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Directory where all bot-related files are stored
BASE_DIR = os.path.join(os.getcwd(), "Discord Bot")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Global in-memory game tracking
games = {}


# ---------------- Utility Functions ---------------- #

def get_server_file(ctx):
    """Returns the correct JSON file path for a given server."""
    server_id = str(ctx.guild.id)
    filename = os.path.join(BASE_DIR, f"{server_id}.json")

    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)

    if not os.path.exists(filename):
        with open(filename, "w") as file:
            json.dump({}, file)  # Creates an empty JSON file

    return filename


def load_server_data(ctx):
    """Loads JSON file for the current server."""
    filename = get_server_file(ctx)
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_server_data(ctx, data):
    """Saves JSON file for the current server."""
    filename = get_server_file(ctx)
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)


def get_birthdays_file():
    """Returns the correct path for the birthdays JSON file inside Discord Bot folder."""
    return os.path.join(BASE_DIR, "birthdays.json")


# ---------------- Command: Set Favorite Team ---------------- #

VALID_LEAGUES = {
    "NFL": ["Bills","Cardinals","Ravens","Falcons","Panthers","Bengals","Bears","Browns","Cowboys","Broncos","Lions","Texans","Packers","Colts","Rams","Jaguars","Vikings","Chiefs","Saints","Raiders","Giants","Chargers","Eagles","Dolphins","49ers","Patriots","Seahawks","Jets","Buccaneers","Steelers","Commanders","Titans"],  # List of valid NFL teams
    "NBA": ["Clippers","Celtics","Nets","Knicks","76ers","Raptors","Bulls","Cavaliers","Pistons","Pacers","Bucks","Hawks","Hornets","Heat","Magic","Wizards","Nuggets","Timberwolves","Thunder","Blazers","Jazz","Warriors","Lakers","Suns","Kings","Mavericks","Rockets","Grizzlies","Pelicans","Spurs"],  # List of valid NBA teams
    "NHL": ["Kings","Hurricanes","Bruins","Jackets","Sabres","Devils","Wings","Islanders","Panthers","Rangers","Canadiens","Flyers","Senators","Penguins","Lightning","Capitals","Leafs","Blackhawks","Ducks","Avalanche","Flames","Stars","Oilers","Wild","Predators","Sharks","Blues","Kraken","Utah","Canucks","Jets","Knights",]   # List of valid NHL teams
}

@bot.command()
async def set_team(ctx, league: str, team: str):
    """Users can set their favorite team using !set_team <league> <team>."""
    league, team = league.upper(), team.title()

    if league not in VALID_LEAGUES or team not in VALID_LEAGUES[league]:
        await ctx.send(f"⚠️ Invalid league or team! Available leagues: {', '.join(VALID_LEAGUES.keys())}")
        return

    data = load_server_data(ctx)
    user_id = str(ctx.author.id)

    data.setdefault(user_id, {}).setdefault("teams", {})[league] = team
    save_server_data(ctx, data)

    await ctx.send(f"✅ {ctx.author.mention}, your favorite **{league}** team is now **{team}**!")


# ---------------- Command: Set Birthday ---------------- #

@bot.command()
async def set_birthday(ctx, month: int, day: int):
    """Users can register their birthday using !set_birthday MM DD."""
    if not (1 <= month <= 12 and 1 <= day <= 31):
        await ctx.send("⚠️ Invalid date! Format: `!set_birthday MM DD`.")
        return

    data = load_server_data(ctx)
    data[str(ctx.author.id)] = {"month": month, "day": day}
    save_server_data(ctx, data)

    await ctx.send(f"🎉 {ctx.author.mention}, your birthday is set to **{month}/{day}**!")


@bot.command()
async def remove_birthday(ctx):
    """Allows users to remove their stored birthday."""
    data = load_server_data(ctx)
    user_id = str(ctx.author.id)

    if user_id in data:
        del data[user_id]
        save_server_data(ctx, data)
        await ctx.send(f"✅ {ctx.author.mention}, your birthday has been removed!")
    else:
        await ctx.send(f"⚠️ {ctx.author.mention}, you don't have a birthday set!")


# ---------------- Rock-Paper-Scissors Game ---------------- #

@bot.command()
async def rps(ctx, choice: str):
    """Play Rock Paper Scissors: LOTR Edition!"""
    choices = {"orc": 1, "hobbit": 2, "elf": 3}
    winning_combos = [(1, 2), (2, 3), (3, 1)]

    choice = choice.lower()
    if choice not in choices:
        await ctx.send("⚠️ Invalid choice! Choose **Orc, Hobbit, or Elf**.")
        return

    user_value = choices[choice]
    comp_value = random.randint(1, 3)
    comp_choice = [k for k, v in choices.items() if v == comp_value][0]

    outcome = "draws" if user_value == comp_value else "wins" if (user_value, comp_value) in winning_combos else "losses"
    result_msg = f"🎉 You win!" if outcome == "wins" else f"😔 You lose!" if outcome == "losses" else "It's a draw!"

    data = load_server_data(ctx)
    data.setdefault(str(ctx.author.id), {}).setdefault("rps_stats", {"wins": 0, "losses": 0, "draws": 0})[outcome] += 1
    save_server_data(ctx, data)

    stats = data[str(ctx.author.id)]["rps_stats"]
    await ctx.send(f"🛡️ **{choice.capitalize()}** vs. 🤖 **{comp_choice.capitalize()}**\n{result_msg}\n"
                   f"📊 Your Record: **{stats['wins']}W - {stats['losses']}L - {stats['draws']}D**")


# ---------------- Task: Birthday Announcements ---------------- #

@tasks.loop(hours=24)
async def check_birthdays():
    """Automatically checks for birthdays and announces them."""
    today = datetime.now()
    for filename in os.listdir(BASE_DIR):
        if filename.endswith(".json"):
            with open(os.path.join(BASE_DIR, filename), "r") as file:
                data = json.load(file)

            for user_id, bday in data.items():
                if "month" in bday and "day" in bday and bday["month"] == today.month and bday["day"] == today.day:
                    user = await bot.fetch_user(int(user_id))
                    if user:
                        guild_id = filename.replace(".json", "")
                        guild = bot.get_guild(int(guild_id))
                        if guild:
                            channel = discord.utils.get(guild.text_channels, name="💬general")
                            if channel:
                                await channel.send(f"🎉 @everyone Happy Birthday, {user.mention}! 🎂🎁")


@bot.event
async def on_ready():
    """Triggers when bot connects to Discord."""
    print(f"{bot.user} is online!")

    if not check_birthdays.is_running():
        check_birthdays.start()
# ------------------TicTacToe--------------------- #
def update_tictactoe_stats(ctx, outcome):
    """Updates the user's Tic-Tac-Toe stats in the JSON file."""
    server_file = get_server_file(ctx)

    try:
        with open(server_file, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    user_id = str(ctx.author.id)

    # Ensure user stats exist
    if user_id not in data:
        data[user_id] = {"tictactoe_stats": {"wins": 0, "losses": 0, "draws": 0}}

    if "tictactoe_stats" not in data[user_id]:
        data[user_id]["tictactoe_stats"] = {"wins": 0, "losses": 0, "draws": 0}

    # Update stats
    if outcome == "win":
        data[user_id]["tictactoe_stats"]["wins"] += 1
    elif outcome == "lose":
        data[user_id]["tictactoe_stats"]["losses"] += 1
    elif outcome == "draw":
        data[user_id]["tictactoe_stats"]["draws"] += 1

    # Save updated stats
    with open(server_file, "w") as file:
        json.dump(data, file, indent=4)

    return data[user_id]["tictactoe_stats"]  # Return updated stats

@bot.command()
async def tictactoe(ctx):
    """Starts a new Tic-Tac-Toe game."""
    user_id = str(ctx.author.id)

    if user_id in games:
        await ctx.send(f"{ctx.author.mention}, you already have an active game! Use `!move <1-9>`.")
        return

    board = [" "] * 9

    def display_board(board):
        return f"""```
 {board[0]} | {board[1]} | {board[2]} 
---+---+---
 {board[3]} | {board[4]} | {board[5]} 
---+---+---
 {board[6]} | {board[7]} | {board[8]} 
```"""

    games[user_id] = {"board": board, "turn": "user"}
    await ctx.send(f"{ctx.author.mention} started a game of Tic-Tac-Toe!\nUse `!move <1-9>` to play.\n{display_board(board)}")

@bot.command()
async def move(ctx, position: int):
    """Handles the user's move in Tic-Tac-Toe."""
    user_id = str(ctx.author.id)

    if user_id not in games:
        await ctx.send(f"{ctx.author.mention}, you don't have an active game! Start one with `!tictactoe`.")
        return

    board = games[user_id]["board"]

    if position < 1 or position > 9 or board[position - 1] != " ":
        await ctx.send(f"{ctx.author.mention}, invalid move! Choose an open spot (1-9).")
        return

    board[position - 1] = "X"

    def display_board(board):
        return f"""```
 {board[0]} | {board[1]} | {board[2]} 
---+---+---
 {board[3]} | {board[4]} | {board[5]} 
---+---+---
 {board[6]} | {board[7]} | {board[8]} 
```"""

    def check_winner(board, player):
        win_conditions = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        return any(all(board[i] == player for i in condition) for condition in win_conditions)

    if check_winner(board, "X"):
        stats = update_tictactoe_stats(ctx, "win")
        await ctx.send(f"🎉 {ctx.author.mention} wins!\n{display_board(board)}\n"
                       f"Your Tic-Tac-Toe Record: {stats['wins']}W / {stats['losses']}L / {stats['draws']}D")
        del games[user_id]
        return

    if " " not in board:
        stats = update_tictactoe_stats(ctx, "draw")
        await ctx.send(f"🤝 It's a draw!\n{display_board(board)}\n"
                       f"Your Tic-Tac-Toe Record: {stats['wins']}W / {stats['losses']}L / {stats['draws']}D")
        del games[user_id]
        return

    await ctx.send(f"Now it's my turn!")

    bot_position = None

    for i in range(9):
        if board[i] == " ":
            board[i] = "O"
            if check_winner(board, "O"):
                bot_position = i
                break
            board[i] = " "

    if bot_position is None and random.random() < 0.9:
        for i in range(9):
            if board[i] == " ":
                board[i] = "X"
                if check_winner(board, "X"):
                    bot_position = i
                    break
                board[i] = " "

    if bot_position is None and board[4] == " ":
        bot_position = 4

    if bot_position is None:
        possible_moves = [i for i in range(9) if board[i] == " "]
        bot_position = random.choice(possible_moves[:2]) if len(possible_moves) >= 2 else possible_moves[0]

    board[bot_position] = "O"

    if check_winner(board, "O"):
        stats = update_tictactoe_stats(ctx, "lose")
        await ctx.send(f"🤖 The bot wins!\n{display_board(board)}\n"
                       f"Your Tic-Tac-Toe Record: {stats['wins']}W / {stats['losses']}L / {stats['draws']}D")
        del games[user_id]
        return

    if " " not in board:
        stats = update_tictactoe_stats(ctx, "draw")
        await ctx.send(f"🤝 It's a draw!\n{display_board(board)}\n"
                       f"Your Tic-Tac-Toe Record: {stats['wins']}W / {stats['losses']}L / {stats['draws']}D")
        del games[user_id]
        return

    await ctx.send(f"Your turn, {ctx.author.mention}!\n{display_board(board)}")
# -----------------Help Command------------------ #
@bot.command()
async def commands(ctx):
    """Displays all available bot commands."""
    commands_list = {
        "!set_team <league> <team>": "Set your favorite team.",
        "!set_birthday <MM> <DD>": "Set your birthday.",
        "!remove_birthday": "Remove your stored birthday.",
        "!rps <orc/hobbit/elf>": "Play Rock-Paper-Scissors (LOTR Edition).",
        "!tictactoe": "Start a game of Tic-Tac-Toe.",
        "!move <1-9>": "Make a move in an active Tic-Tac-Toe game."
    }

    help_message = "**📜 Available Commands:**\n"
    for command, description in commands_list.items():
        help_message += f"**{command}** - {description}\n"

    await ctx.send(help_message)


# ---------------- Run the Bot ---------------- #
bot.run(TOKEN)
