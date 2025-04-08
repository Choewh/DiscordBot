import discord
from discord.ext import commands
import re
from typing import List, Dict, Optional
import asyncio

class ForbiddenWordGame:
    def __init__(self):
        self.is_active = False
        self.forbidden_word = None
        self.players: List[discord.Member] = []
        self.game_channel = None
        self.eliminated_players: List[discord.Member] = []
        self.message_history: Dict[int, List[str]] = {}  # user_id: [messages]
        
    def start_game(self, channel: discord.TextChannel) -> str:
        if self.is_active:
            return "이미 게임이 진행 중입니다."
        self.is_active = True
        self.game_channel = channel
        return "금칙어 게임이 시작되었습니다. `/금칙어 [단어]` 명령어로 금칙어를 설정해주세요."
    
    def set_forbidden_word(self, word: str) -> str:
        if not self.is_active:
            return "게임이 시작되지 않았습니다. `/시작` 명령어로 게임을 시작해주세요."
        self.forbidden_word = word
        return f"금칙어가 '{word}'로 설정되었습니다. `/참가` 명령어로 게임에 참가해주세요."
    
    def join_game(self, player: discord.Member) -> str:
        if not self.is_active:
            return "게임이 시작되지 않았습니다."
        if player in self.players:
            return "이미 게임에 참가하셨습니다."
        if player in self.eliminated_players:
            return "이미 탈락하셨습니다."
        self.players.append(player)
        self.message_history[player.id] = []
        return f"{player.mention}님이 게임에 참가하셨습니다."
    
    def check_message(self, message: discord.Message) -> Optional[str]:
        if not self.is_active or not self.forbidden_word:
            return None
        if message.author not in self.players or message.author in self.eliminated_players:
            return None
            
        content = message.content.lower()
        # 맞춤법 교정 로직 (실제로는 더 복잡한 로직이 필요)
        content = re.sub(r'[^\w\s]', '', content)  # 특수문자 제거
        
        if self.forbidden_word.lower() in content:
            self.eliminated_players.append(message.author)
            self.players.remove(message.author)
            return f"{message.author.mention}님이 금칙어 '{self.forbidden_word}'를 사용하여 탈락하셨습니다!"
        return None
    
    def get_players(self) -> str:
        if not self.is_active:
            return "게임이 시작되지 않았습니다."
        
        players_list = "\n".join([f"• {player.name}" for player in self.players])
        eliminated_list = "\n".join([f"• {player.name}" for player in self.eliminated_players])
        
        return f"**참가자 목록**\n{players_list}\n\n**탈락자 목록**\n{eliminated_list}"
    
    def end_game(self) -> str:
        if not self.is_active:
            return "게임이 시작되지 않았습니다."
        
        winner = self.players[0] if len(self.players) == 1 else None
        result = "게임이 종료되었습니다.\n"
        
        if winner:
            result += f"승자: {winner.mention}님"
        else:
            result += "승자가 없습니다."
            
        self.is_active = False
        self.forbidden_word = None
        self.players = []
        self.eliminated_players = []
        self.message_history = {}
        self.game_channel = None
        
        return result

class ForbiddenWordCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.game = ForbiddenWordGame()
        
    @commands.command(name="시작")
    async def start_game(self, ctx):
        """금칙어 게임을 시작합니다."""
        response = self.game.start_game(ctx.channel)
        await ctx.send(response)
        
    @commands.command(name="금칙어")
    async def set_forbidden_word(self, ctx, word: str):
        """금칙어를 설정합니다."""
        response = self.game.set_forbidden_word(word)
        await ctx.send(response)
        
    @commands.command(name="참가")
    async def join_game(self, ctx):
        """게임에 참가합니다."""
        response = self.game.join_game(ctx.author)
        await ctx.send(response)
        
    @commands.command(name="참가자")
    async def show_players(self, ctx):
        """현재 참가자 목록을 보여줍니다."""
        response = self.game.get_players()
        await ctx.send(response)
        
    @commands.command(name="종료")
    async def end_game(self, ctx):
        """게임을 종료합니다."""
        response = self.game.end_game()
        await ctx.send(response)
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
            
        if self.game.is_active and self.game.game_channel == message.channel:
            result = self.game.check_message(message)
            if result:
                await message.channel.send(result)
                
                # 게임 종료 조건 체크
                if len(self.game.players) <= 1:
                    await message.channel.send(self.game.end_game())
                    
        await self.bot.process_commands(message)

def setup(bot):
    bot.add_cog(ForbiddenWordCog(bot)) 