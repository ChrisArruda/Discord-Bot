import random
import discord
from discord.ext import commands, tasks
from typing import Optional, Dict, List, Tuple, Any

from ..utils.database import db

class Games(commands.Cog):
    """Game commands including Tic-Tac-Toe and Rock-Paper-Scissors."""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games: Dict[int, Dict] = {}  # user_id -> game_data
    
    # ===== TIC-TAC-TOE GAME =====
    
    @commands.hybrid_command(name="tictactoe", aliases=["ttt"], description="Start a new Tic-Tac-Toe game")
    async def tictactoe(self, ctx):
        """Start a new Tic-Tac-Toe game against the bot."""
        if ctx.author.id in self.active_games:
            await ctx.send("You already have an active game! Use `!move <1-9>` to play.", ephemeral=True)
            return
        
        # Initialize game board
        board = [" " for _ in range(9)]
        self.active_games[ctx.author.id] = {
            "board": board,
            "game_type": "tictactoe"
        }
        
        # Send initial board
        board_display = self._format_ttt_board(board)
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Tic-Tac-Toe Game",
            description=f"Use `{ctx.prefix}move <1-9>` to make a move.\n\n{board_display}",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Positions",
            value="```\n1 | 2 | 3\n--------\n4 | 5 | 6\n--------\n7 | 8 | 9\n```",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="move", description="Make a move in Tic-Tac-Toe")
    async def make_move(self, ctx, position: int):
        """Make a move in your Tic-Tac-Toe game."""
        if ctx.author.id not in self.active_games:
            await ctx.send("You don't have an active game! Start one with `!tictactoe`.", ephemeral=True)
            return
            
        game = self.active_games[ctx.author.id]
        board = game["board"]
        
        # Validate move
        if not (1 <= position <= 9):
            await ctx.send("Please choose a position between 1 and 9.", ephemeral=True)
            return
            
        if board[position - 1] != " ":
            await ctx.send("That position is already taken!", ephemeral=True)
            return
        
        # Player's move
        board[position - 1] = "X"
        
        # Check if player won
        if self._check_ttt_win(board, "X"):
            await self._end_game(ctx, "win")
            return
            
        # Check for draw
        if " " not in board:
            await self._end_game(ctx, "draw")
            return
            
        # Bot's move
        bot_move = self._get_bot_move(board)
        board[bot_move] = "O"
        
        # Check if bot won
        if self._check_ttt_win(board, "O"):
            await self._end_game(ctx, "lose")
            return
            
        # Check for draw after bot's move
        if " " not in board:
            await self._end_game(ctx, "draw")
            return
            
        # Game continues
        board_display = self._format_ttt_board(board)
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Tic-Tac-Toe Game",
            description=f"Your turn! Use `{ctx.prefix}move <1-9>`\n\n{board_display}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    
    def _format_ttt_board(self, board: List[str]) -> str:
        """Format the Tic-Tac-Toe board for display."""
        return f"""```
 {board[0]} | {board[1]} | {board[2]} 
-----------
 {board[3]} | {board[4]} | {board[5]} 
-----------
 {board[6]} | {board[7]} | {board[8]} 
```"""
    
    def _check_ttt_win(self, board: List[str], player: str) -> bool:
        """Check if the specified player has won."""
        win_conditions = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]              # Diagonals
        ]
        return any(all(board[i] == player for i in condition) for condition in win_conditions)
    
    def _get_bot_move(self, board: List[str]) -> int:
        """Determine the bot's move using a simple AI."""
        # Check for winning move
        for i in range(9):
            if board[i] == " ":
                board[i] = "O"
                if self._check_ttt_win(board, "O"):
                    board[i] = " "  # Undo the move
                    return i
                board[i] = " "  # Undo the move
        
        # Block player's winning move
        for i in range(9):
            if board[i] == " ":
                board[i] = "X"
                if self._check_ttt_win(board, "X"):
                    board[i] = " "  # Undo the move
                    return i
                board[i] = " "  # Undo the move
        
        # Take center if available
        if board[4] == " ":
            return 4
        
        # Take a corner if available
        corners = [0, 2, 6, 8]
        available_corners = [i for i in corners if board[i] == " "]
        if available_corners:
            return random.choice(available_corners)
        
        # Take any available edge
        edges = [1, 3, 5, 7]
        available_edges = [i for i in edges if board[i] == " "]
        if available_edges:
            return random.choice(available_edges)
        
        # Shouldn't reach here if game isn't over
        return board.index(" ")
    
    async def _end_game(self, ctx, result: str):
        """Handle game end and cleanup."""
        user_id = ctx.author.id
        board = self.active_games[user_id]["board"]
        
        # Update stats
        if result in ["win", "lose", "draw"]:
            # Get current stats
            user_data = db.ensure_user_profile(ctx.guild.id, user_id)
            stats = user_data.setdefault("tictactoe_stats", {"wins": 0, "losses": 0, "draws": 0})
            
            # Update stats
            if result == "win":
                stats["wins"] = stats.get("wins", 0) + 1
                result_msg = "🎉 You win!"
            elif result == "lose":
                stats["losses"] = stats.get("losses", 0) + 1
                result_msg = "😢 You lose!"
            else:  # draw
                stats["draws"] = stats.get("draws", 0) + 1
                result_msg = "🤝 It's a draw!"
            
            # Save updated stats
            db.update_user_data(ctx.guild.id, user_id, tictactoe_stats=stats)
        
        # Send final board
        board_display = self._format_ttt_board(board)
        embed = discord.Embed(
            title=f"Game Over - {result_msg}",
            description=f"{board_display}\nYour record: {stats['wins']}W - {stats['losses']}L - {stats['draws']}D",
            color=discord.Color.gold() if result == "win" else discord.Color.red() if result == "lose" else discord.Color.light_grey()
        )
        
        await ctx.send(embed=embed)
        del self.active_games[user_id]  # Remove the game
    
    # ===== ROCK-PAPER-SCISSORS GAME =====
    
    @commands.hybrid_command(name="rps", description="Play Rock-Paper-Scissors (LOTR Edition)")
    async def rock_paper_scissors(self, ctx, choice: str):
        """Play Rock-Paper-Scissors with the bot (LOTR Edition).
        
        Choices: orc (rock), hobbit (paper), elf (scissors)
        """
        choice = choice.lower()
        choices = {"orc": "🪨 Orc", "hobbit": "📜 Hobbit", "elf": "✂️ Elf"}
        
        if choice not in choices:
            await ctx.send(
                "⚠️ Invalid choice! Choose **orc**, **hobbit**, or **elf**.",
                ephemeral=True
            )
            return
        
        # Get bot's choice
        bot_choice = random.choice(list(choices.keys()))
        
        # Determine winner
        if choice == bot_choice:
            result = "draw"
            result_msg = "It's a draw!"
        elif (choice == "orc" and bot_choice == "elf") or \
             (choice == "hobbit" and bot_choice == "orc") or \
             (choice == "elf" and bot_choice == "hobbit"):
            result = "win"
            result_msg = "You win! 🎉"
        else:
            result = "lose"
            result_msg = "You lose! 😢"
        
        # Update stats
        user_data = db.ensure_user_profile(ctx.guild.id, ctx.author.id)
        stats = user_data.setdefault("rps_stats", {"wins": 0, "losses": 0, "draws": 0})
        
        if result == "win":
            stats["wins"] = stats.get("wins", 0) + 1
        elif result == "lose":
            stats["losses"] = stats.get("losses", 0) + 1
        else:  # draw
            stats["draws"] = stats.get("draws", 0) + 1
        
        db.update_user_data(ctx.guild.id, ctx.author.id, rps_stats=stats)
        
        # Send result
        embed = discord.Embed(
            title=f"{choices[choice]} vs {choices[bot_choice]}",
            description=f"**{result_msg}**\n\n"
                      f"Your record: {stats['wins']}W - {stats['losses']}L - {stats['draws']}D",
            color=discord.Color.green() if result == "win" else 
                  discord.Color.red() if result == "lose" else 
                  discord.Color.blue()
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Games(bot))
