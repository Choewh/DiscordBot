import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
import re
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

# YouTube-DL options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'socket_timeout': 30,
    'retries': 5,
    'buffersize': 1024 * 16,
    'http_chunk_size': 10485760,
}

# 플레이리스트용 YouTube-DL 옵션
playlist_ytdl_options = ytdl_format_options.copy()
playlist_ytdl_options['noplaylist'] = False  # 플레이리스트 처리 활성화
playlist_ytdl = yt_dlp.YoutubeDL(playlist_ytdl_options)

# Set ffmpeg path - change this to your FFmpeg path if not in system PATH
FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'ffmpeg')  # Default to 'ffmpeg' if not specified

ffmpeg_options = {
    'options': '-vn -b:a 128k -bufsize 512k -ar 48000 -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10',
    'executable': FFMPEG_PATH,
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class MusicPlayer:
    def __init__(self):
        self.queue = []
        self.current = None
        self.voice_client = None
        self.is_playing = False
        self.volume = 0.5  # 기본 음량을 50%로 설정
        self.retry_count = 0
        self.max_retries = 3

    async def play_next(self):
        if self.is_playing:
            return
            
        if not self.queue:
            self.is_playing = False
            return
        
        if not self.voice_client or not self.voice_client.is_connected():
            self.is_playing = False
            return

        self.is_playing = True
        
        try:
            self.current = self.queue.pop(0)
            source = discord.FFmpegPCMAudio(
                self.current['url'],
                **ffmpeg_options
            )
            volume_source = discord.PCMVolumeTransformer(source, volume=self.volume)
            self.voice_client.play(volume_source, after=lambda e: asyncio.run_coroutine_threadsafe(self._play_next_callback(e), bot.loop))
            self.retry_count = 0  # 재생 성공 시 재시도 카운트 초기화
            
        except Exception as e:
            print(f"Error playing audio: {e}")
            self.is_playing = False
            await self.play_next()
    
    async def _play_next_callback(self, error):
        if error:
            print(f"Player error: {error}")
            self.retry_count += 1
            
            # 오류 발생 시 재시도
            if self.retry_count < self.max_retries:
                print(f"Retrying playback (attempt {self.retry_count}/{self.max_retries})")
                # 현재 곡을 다시 큐에 추가
                if self.current:
                    self.queue.insert(0, self.current)
        
        self.is_playing = False
        await self.play_next()

player = MusicPlayer()

class ForbiddenWordGame:
    def __init__(self):
        self.is_active = False
        self.forbidden_words = {}  # player_id: forbidden_word
        self.players: List[discord.Member] = []
        self.game_channel = None
        self.eliminated_players: List[discord.Member] = []
        self.message_history: Dict[int, List[str]] = {}  # user_id: [messages]
        self.min_players = 2  # 최소 2명 이상 필요
        self.pending_forbidden_words = {}  # player_id: target_id (누구의 금칙어를 설정해야 하는지)
        
    async def send(self, content: str, ephemeral: bool = False) -> None:
        """게임 채널에 메시지를 보냅니다."""
        if self.game_channel:
            await self.game_channel.send(content)
            
    async def start_game(self, channel: discord.TextChannel) -> str:
        if self.is_active:
            return "이미 게임이 진행 중입니다."
        
        if len(self.players) < self.min_players:
            return f"게임을 시작하려면 최소 {self.min_players}명의 참가자가 필요합니다. 현재 참가자 수: {len(self.players)}명"
            
        self.is_active = True
        self.game_channel = channel
        
        # 각 플레이어에게 다른 플레이어의 금칙어를 설정하도록 배정
        import random
        player_indices = list(range(len(self.players)))
        random.shuffle(player_indices)
        
        # 순환 구조로 각 플레이어에게 다른 플레이어를 배정
        for i in range(len(self.players)):
            target_index = (i + 1) % len(self.players)
            self.pending_forbidden_words[self.players[i].id] = self.players[target_index].id
        
        # 게임 시작 안내 메시지
        await channel.send("🎮 금칙어 게임이 시작되었습니다!")
        
        # 참여자가 6명 이하인 경우 채널에 임베드 메시지로 안내
        if len(self.players) <= 6:
            # 임베드 메시지 생성
            embed = discord.Embed(
                title="🎯 금칙어 설정 안내",
                description="각 플레이어는 배정된 대상의 금칙어를 설정해주세요.",
                color=discord.Color.blue()
            )
            
            # 각 플레이어의 설정 안내 추가
            for player in self.players:
                target_id = self.pending_forbidden_words[player.id]
                target = next((p for p in self.players if p.id == target_id), None)
                if target:
                    embed.add_field(
                        name=f"{player.name}님의 설정",
                        value=f"{player.mention}님, {target.name}님의 금칙어를 설정해주세요.",
                        inline=False
                    )
            
            # 설정 방법 안내 추가
            embed.add_field(
                name="설정 방법",
                value="`/금칙어 단어` 형식으로 입력하세요.",
                inline=False
            )
            
            # 게임 시작 조건 안내 추가
            embed.add_field(
                name="게임 시작",
                value="모든 플레이어가 금칙어를 설정하면 게임이 시작됩니다!",
                inline=False
            )
            
            # 임베드 메시지 전송
            await channel.send(embed=embed)
        else:
            # 참여자가 6명 초과인 경우 DM으로 안내
            await channel.send("참여자가 많아 각 플레이어에게 DM으로 금칙어 설정 안내를 보냅니다.")
            
            # 각 플레이어에게 DM으로 안내
            for player in self.players:
                target_id = self.pending_forbidden_words[player.id]
                target = next((p for p in self.players if p.id == target_id), None)
                if target:
                    try:
                        # DM으로 안내 메시지 전송
                        embed = discord.Embed(
                            title="🎯 금칙어 설정 안내",
                            description=f"{player.name}님, {target.name}님의 금칙어를 설정해주세요.",
                            color=discord.Color.blue()
                        )
                        embed.add_field(
                            name="설정 방법",
                            value="`/금칙어 단어` 형식으로 입력하세요.",
                            inline=False
                        )
                        await player.send(embed=embed)
                    except discord.errors.Forbidden:
                        # DM이 차단된 경우 채널에 메시지 전송
                        await channel.send(f"{player.mention}님, DM이 차단되어 있습니다. 채널에서 금칙어를 설정해주세요.")
        
        return f"금칙어 게임이 시작되었습니다! 현재 참가자: {len(self.players)}명\n각 플레이어에게 금칙어 설정 안내를 보냈습니다."
    
    def set_forbidden_word(self, word: str, setter: discord.Member) -> str:
        if not self.is_active:
            return "게임이 시작되지 않았습니다. `/시작` 명령어로 게임을 시작해주세요."
        
        if setter.id not in self.pending_forbidden_words:
            return "당신은 금칙어를 설정할 차례가 아닙니다."
            
        target_id = self.pending_forbidden_words[setter.id]
        target = next((p for p in self.players if p.id == target_id), None)
        
        if not target:
            return "금칙어를 설정할 대상이 없습니다."
            
        if target.id in self.forbidden_words:
            return f"{target.name}님의 금칙어가 이미 설정되어 있습니다."
            
        self.forbidden_words[target.id] = word
        del self.pending_forbidden_words[setter.id]
        
        # 설정된 플레이어 수와 전체 플레이어 수 계산
        set_count = len(self.forbidden_words)
        total_count = len(self.players)
        
        # 모든 금칙어가 설정되었는지 확인
        if not self.pending_forbidden_words:
            asyncio.create_task(self.game_channel.send(
                "🎉 모든 플레이어의 금칙어가 설정되었습니다!\n"
                "이제 게임이 본격적으로 시작됩니다.\n"
                "각자의 금칙어를 피해서 대화를 나누세요. 금칙어를 사용하면 탈락합니다!"
            ))
        else:
            # 아직 설정되지 않은 플레이어 목록 생성
            remaining_players = [p.name for p in self.players if p.id not in self.forbidden_words]
            asyncio.create_task(self.game_channel.send(
                f"✅ {target.name}님의 금칙어가 설정되었습니다! ({set_count}/{total_count})\n"
                f"아직 금칙어를 설정하지 않은 플레이어: {', '.join(remaining_players)}"
            ))
        
        return f"{target.name}님의 금칙어가 '{word}'로 설정되었습니다."
    
    def join_game(self, player: discord.Member) -> str:
        if self.is_active:
            return "게임이 이미 시작되었습니다. 다음 게임에 참가해주세요."
        if player in self.players:
            return "이미 게임에 참가하셨습니다."
        if player in self.eliminated_players:
            return "이미 탈락하셨습니다."
        self.players.append(player)
        self.message_history[player.id] = []
        return f"{player.mention}님이 게임에 참가하셨습니다. (현재 참가자: {len(self.players)}명)"
    
    def check_message(self, message: discord.Message) -> Optional[str]:
        if not self.is_active:
            return None
        if message.author not in self.players or message.author in self.eliminated_players:
            return None
            
        content = message.content.lower()
        # 맞춤법 교정 로직 (실제로는 더 복잡한 로직이 필요)
        content = re.sub(r'[^\w\s]', '', content)  # 특수문자 제거
        
        # 해당 플레이어의 금칙어 확인
        forbidden_word = self.forbidden_words.get(message.author.id)
        if forbidden_word and forbidden_word.lower() in content:
            self.eliminated_players.append(message.author)
            self.players.remove(message.author)
            return f"{message.author.mention}님이 금칙어 '{forbidden_word}'를 사용하여 탈락하셨습니다!"
        return None
    
    def get_players(self) -> str:
        if not self.players:
            return "참가자가 없습니다. `/참가` 명령어로 게임에 참가해주세요."
        
        players_list = "\n".join([f"• {player.name}" for player in self.players])
        eliminated_list = "\n".join([f"• {player.name}" for player in self.eliminated_players]) if self.eliminated_players else "없음"
        
        result = f"**참가자 목록** ({len(self.players)}명)\n{players_list}\n\n**탈락자 목록**\n{eliminated_list}"
        
        if self.is_active:
            result += "\n\n**금칙어 설정 현황**"
            for player in self.players:
                if player.id in self.forbidden_words:
                    result += f"\n• {player.name}: 설정됨"
                else:
                    result += f"\n• {player.name}: 미설정"
        
        return result
    
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
        self.forbidden_words = {}
        self.players = []
        self.eliminated_players = []
        self.message_history = {}
        self.game_channel = None
        self.pending_forbidden_words = {}
        
        return result

# 금지어 게임 인스턴스 생성
forbidden_word_game = ForbiddenWordGame()

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user.name}')
    print(f'Using FFmpeg path: {FFMPEG_PATH}')
    
    # 슬래시 명령어 등록
    try:
        await bot.tree.sync()
        print("슬래시 명령어가 등록되었습니다.")
    except Exception as e:
        print(f"슬래시 명령어 등록 중 오류 발생: {e}")

@bot.command(name='musichelp')
async def musichelp(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="🎵 음악 봇 명령어 목록 🎵",
        color=discord.Color.blue(),
        description="음악 봇을 이용하는 데 필요한 명령어들입니다."
    )
    
    # 기본 명령어
    basic_commands = [
        ("/join", "봇을 현재 음성 채널에 참여시킵니다."),
        ("/forcejoin", "봇이 다른 채널에 있어도 강제로 현재 채널로 이동시킵니다."),
        ("/play <URL>", "YouTube 링크로 음악을 재생합니다."),
        ("/playlist <URL>", "YouTube 플레이리스트의 곡들을 재생 목록에 추가합니다.")
    ]
    
    # 제어 명령어
    control_commands = [
        ("/stop", "현재 재생 중인 음악을 중지하고 재생 대기열을 비웁니다."),
        ("/skip", "현재 재생 중인 음악을 건너뜁니다."),
        ("/volume [0-100]", "음량을 설정합니다. 값을 입력하지 않으면 현재 음량을 표시합니다."),
        ("/nowplaying", "현재 재생 중인 곡을 표시합니다."),
        ("/queue", "현재 대기열에 있는 음악 목록을 보여줍니다.")
    ]
    
    # 기본 명령어 필드 추가
    embed.add_field(name="⏯️ 기본 명령어", value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in basic_commands]), inline=False)
    
    # 제어 명령어 필드 추가
    embed.add_field(name="🎛️ 제어 명령어", value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in control_commands]), inline=False)
    
    # 사용 방법 필드 추가
    usage = [
        "1. 음성 채널에 들어갑니다.",
        "2. `/join` 명령어로 봇을 음성 채널에 참여시킵니다.",
        "3. `/play <URL>` 명령어로 음악을 재생합니다.",
        "4. 필요한 경우 `/skip`으로 다음 곡으로 넘어가거나, `/stop`으로 재생을 중지할 수 있습니다."
    ]
    
    embed.add_field(name="📝 사용 방법", value="\n".join(usage), inline=False)
    
    embed.set_footer(text="문제가 있을 경우 관리자에게 문의하세요.")
    
    await ctx.send(embed=embed)

@bot.command()
async def join(ctx):
    """Join the user's voice channel"""
    if not ctx.author.voice:
        await ctx.send('음성 채널에 먼저 들어가주세요!')
        return
        
    # 봇이 이미 다른 음성 채널에 있는지 확인
    if player.voice_client and player.voice_client.is_connected():
        if player.voice_client.channel.id != ctx.author.voice.channel.id:
            await ctx.send(f'봇이 이미 다른 채널 `/{player.voice_client.channel.name}`에서 사용 중입니다. 강제로 이동시키려면 `/forcejoin` 명령어를 사용하세요.')
            return
        else:
            await ctx.send(f'봇이 이미 현재 채널에 있습니다!')
            return
    
    # 봇이 음성 채널에 입장
    channel = ctx.author.voice.channel
    player.voice_client = await channel.connect()
    await ctx.send(f'`{channel}` 채널에 입장했습니다.')

@bot.command()
async def forcejoin(ctx):
    """Force the bot to join the user's voice channel even if it's already in another channel"""
    if not ctx.author.voice:
        await ctx.send('음성 채널에 먼저 들어가주세요!')
        return
        
    # 봇이 이미 다른 음성 채널에 있는지 확인
    if player.voice_client and player.voice_client.is_connected():
        if player.voice_client.channel.id != ctx.author.voice.channel.id:
            # 현재 재생 중인 음악 중지
            player.voice_client.stop()
            await player.voice_client.disconnect()
            await ctx.send(f'`{player.voice_client.channel.name}` 채널에서 연결을 해제했습니다.')
    
    # 봇이 새 음성 채널에 입장
    channel = ctx.author.voice.channel
    player.voice_client = await channel.connect()
    await ctx.send(f'`{channel}` 채널에 강제 입장했습니다.')

@bot.command()
async def play(ctx, url):
    """Play a YouTube video"""
    if not ctx.author.voice:
        await ctx.send('음성 채널에 먼저 들어가주세요!')
        return

    # 봇이 이미 다른 음성 채널에 있는지 확인
    if player.voice_client and player.voice_client.is_connected():
        if player.voice_client.channel.id != ctx.author.voice.channel.id:
            await ctx.send(f'봇이 이미 다른 채널 `/{player.voice_client.channel.name}`에서 사용 중입니다. 강제로 이동시키려면 `/forcejoin` 명령어를 사용 후 다시 시도하세요.')
            return

    if not player.voice_client:
        await ctx.invoke(bot.get_command('join'))

    try:
        await ctx.send('음악을 불러오는 중입니다. 잠시만 기다려주세요...')
        info = ytdl.extract_info(url, download=False)
        player.queue.append({
            'url': info['url'],
            'title': info['title']
        })
        
        if not player.is_playing:
            await player.play_next()
        
        await ctx.send(f'재생 목록에 추가됨: `{info["title"]}`')
    except Exception as e:
        await ctx.send(f'오류: {str(e)}')

@bot.command()
async def stop(ctx):
    """Stop playing and clear the queue"""
    if player.voice_client:
        player.voice_client.stop()
        player.queue.clear()
        player.is_playing = False
        await ctx.send('재생을 중지하고 대기열을 비웠습니다.')
    else:
        await ctx.send('재생 중인 음악이 없습니다!')

@bot.command()
async def skip(ctx):
    """Skip the current song"""
    if player.voice_client and player.is_playing:
        player.voice_client.stop()
        player.is_playing = False
        await ctx.send('현재 곡을 건너뛰었습니다.')
    else:
        await ctx.send('재생 중인 음악이 없습니다!')

@bot.command()
async def queue(ctx):
    """Show the current queue"""
    if not player.queue:
        await ctx.send('대기열이 비어있습니다!')
        return
    
    queue_list = '\n'.join([f'{i+1}. {song["title"]}' for i, song in enumerate(player.queue)])
    await ctx.send(f'현재 대기열:\n{queue_list}')

@bot.command()
async def nowplaying(ctx):
    """Show the currently playing song"""
    if player.current and player.is_playing:
        embed = discord.Embed(
            title="🎵 현재 재생 중",
            description=f"`{player.current['title']}`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("현재 재생 중인 음악이 없습니다!")

@bot.command()
async def volume(ctx, volume: int = None):
    """Set the player volume (0-100)"""
    if not player.voice_client:
        return await ctx.send("봇이 음성 채널에 연결되어 있지 않습니다!")
    
    if volume is None:
        # 현재 음량을 퍼센트로 표시
        current_volume = int(player.volume * 100)
        return await ctx.send(f"현재 음량: {current_volume}%")
    
    if not 0 <= volume <= 100:
        return await ctx.send("음량은 0에서 100 사이의 값이어야 합니다!")
    
    # 음량을 0.0 ~ 1.0 사이의 값으로 설정
    player.volume = volume / 100
    if player.voice_client.source:
        player.voice_client.source.volume = player.volume
    
    await ctx.send(f"음량을 {volume}%로 설정했습니다.")

@bot.command()
async def playlist(ctx, url):
    """Play a YouTube playlist"""
    if not ctx.author.voice:
        await ctx.send('음성 채널에 먼저 들어가주세요!')
        return

    # 봇이 이미 다른 음성 채널에 있는지 확인
    if player.voice_client and player.voice_client.is_connected():
        if player.voice_client.channel.id != ctx.author.voice.channel.id:
            await ctx.send(f'봇이 이미 다른 채널 `/{player.voice_client.channel.name}`에서 사용 중입니다. 강제로 이동시키려면 `/forcejoin` 명령어를 사용 후 다시 시도하세요.')
            return

    if not player.voice_client:
        await ctx.invoke(bot.get_command('join'))

    try:
        await ctx.send('플레이리스트를 불러오는 중입니다. 잠시만 기다려주세요...')
        
        # 플레이리스트 정보 가져오기
        info = playlist_ytdl.extract_info(url, download=False)
        
        if 'entries' not in info:
            await ctx.send('유효한 플레이리스트가 아닙니다!')
            return
            
        # 최대 25개 곡만 큐에 추가
        entries = info['entries'][:25]
        
        # 각 곡을 큐에 추가
        added_count = 0
        for entry in entries:
            if entry:
                player.queue.append({
                    'url': entry['url'],
                    'title': entry['title']
                })
                added_count += 1
        
        if not player.is_playing:
            await player.play_next()
        
        await ctx.send(f'플레이리스트에서 {added_count}개의 곡을 재생 목록에 추가했습니다.')
    except Exception as e:
        await ctx.send(f'오류: {str(e)}')

@bot.tree.command(name="search", description="YouTube에서 음악을 검색합니다.")
async def slash_search(interaction: discord.Interaction, query: str):
    """YouTube에서 음악을 검색하고 선택한 곡을 재생합니다."""
    if not interaction.user.voice:
        await interaction.response.send_message("음성 채널에 먼저 입장해주세요!", ephemeral=True)
        return

    await interaction.response.defer()

    try:
        # 검색 옵션 설정
        ydl_opts = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch5',  # 상위 5개 결과만 가져오기
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'socket_timeout': 30,
            'retries': 5,
            'buffersize': 16384
        }

        # 비동기로 검색 실행
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                search_results = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch5:{query}", download=False))
            except Exception as e:
                await interaction.followup.send(f"검색 중 오류가 발생했습니다: {str(e)}")
                return

        if not search_results or 'entries' not in search_results:
            await interaction.followup.send("검색 결과를 찾을 수 없습니다.")
            return

        # 검색 결과 표시
        embed = discord.Embed(
            title="🎵 검색 결과",
            description="재생할 곡의 번호를 입력해주세요 (1-5)\n취소하려면 '취소'를 입력하세요.",
            color=discord.Color.blue()
        )

        for i, entry in enumerate(search_results['entries'], 1):
            if entry:
                title = entry.get('title', '제목 없음')
                duration = entry.get('duration', 0)
                url = f"https://www.youtube.com/watch?v={entry['id']}"
                
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
                
                embed.add_field(
                    name=f"{i}. {title}",
                    value=f"⏱️ {duration_str}\n🔗 {url}",
                    inline=False
                )

        embed.set_footer(text="30초 안에 선택해주세요.")
        search_msg = await interaction.followup.send(embed=embed)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            
            if msg.content.lower() == '취소':
                await interaction.channel.send("검색이 취소되었습니다.")
                await search_msg.delete()
                return

            try:
                choice = int(msg.content)
                if choice < 1 or choice > len(search_results['entries']):
                    await interaction.channel.send("올바른 번호를 입력해주세요 (1-5).")
                    return
            except ValueError:
                await interaction.channel.send("올바른 번호를 입력해주세요 (1-5).")
                return

            selected = search_results['entries'][choice - 1]
            if not selected:
                await interaction.channel.send("선택한 곡을 찾을 수 없습니다.")
                return

            url = f"https://www.youtube.com/watch?v={selected['id']}"
            
            # 검색 결과 메시지 삭제
            await search_msg.delete()
            
            # 재생 명령어 실행
            ctx = await bot.get_context(msg)
            ctx.command = bot.get_command('play')
            await play(ctx, url)

        except asyncio.TimeoutError:
            await interaction.channel.send("시간이 초과되었습니다. 다시 시도해주세요.")
            await search_msg.delete()

    except Exception as e:
        await interaction.followup.send(f"오류가 발생했습니다: {str(e)}")

@bot.command()
async def leave(ctx):
    """Leave the voice channel"""
    if not player.voice_client:
        await ctx.send('봇이 음성 채널에 연결되어 있지 않습니다!')
        return
        
    # 재생 중인 음악 중지
    if player.is_playing:
        player.voice_client.stop()
        player.is_playing = False
        
    # 대기열 비우기
    player.queue.clear()
    
    # 연결 해제
    await player.voice_client.disconnect()
    player.voice_client = None
    
    await ctx.send('음성 채널에서 연결을 해제했습니다.')

@bot.tree.command(name="set_word", description="금칙어를 설정합니다.")
async def slash_set_forbidden_word(interaction: discord.Interaction, word: str):
    """금칙어를 설정합니다."""
    response = forbidden_word_game.set_forbidden_word(word, interaction.user)
    # 에피메럴 메시지로 응답 (특정 사용자에게만 보임)
    await interaction.response.send_message(response, ephemeral=True)

@bot.tree.command(name="game_start", description="금칙어 게임을 시작합니다.")
async def slash_start_game(interaction: discord.Interaction):
    """금칙어 게임을 시작합니다."""
    response = await forbidden_word_game.start_game(interaction.channel)
    await interaction.response.send_message(response)

@bot.tree.command(name="game_join", description="금칙어 게임에 참가합니다.")
async def slash_join_game(interaction: discord.Interaction):
    """게임에 참가합니다."""
    response = forbidden_word_game.join_game(interaction.user)
    await interaction.response.send_message(response)

@bot.tree.command(name="players", description="현재 참가자 목록을 보여줍니다.")
async def slash_show_players(interaction: discord.Interaction):
    """현재 참가자 목록을 보여줍니다."""
    response = forbidden_word_game.get_players()
    await interaction.response.send_message(response)

@bot.tree.command(name="game_end", description="게임을 종료합니다.")
async def slash_end_game(interaction: discord.Interaction):
    """게임을 종료합니다."""
    response = forbidden_word_game.end_game()
    await interaction.response.send_message(response)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
        
    # 사용자가 "/"만 입력했을 때 명령어 목록 표시
    if message.content == "/":
        await show_command_list(message.channel)
        return
        
    if forbidden_word_game.is_active and forbidden_word_game.game_channel == message.channel:
        result = forbidden_word_game.check_message(message)
        if result:
            await message.channel.send(result)
            
            # 게임 종료 조건 체크
            if len(forbidden_word_game.players) <= 1:
                await message.channel.send(forbidden_word_game.end_game())
                
    await bot.process_commands(message)

# 슬래시 명령어: 도움말
@bot.tree.command(name="help", description="사용 가능한 모든 명령어와 설명을 보여줍니다.")
async def help_command(interaction: discord.Interaction):
    await show_command_list(interaction.channel)
    await interaction.response.send_message("도움말을 표시했습니다.", ephemeral=True)

# 슬래시 명령어: 음악 도움말
@bot.tree.command(name="music_help", description="음악 봇 사용법을 자세히 보여줍니다.")
async def music_help_command(interaction: discord.Interaction):
    await interaction.response.send_message(embed=create_music_help_embed(), ephemeral=True)

# 슬래시 명령어: 금칙어 게임 도움말
@bot.tree.command(name="game_help", description="금칙어 게임 사용법을 자세히 보여줍니다.")
async def game_help_command(interaction: discord.Interaction):
    await interaction.response.send_message(embed=create_game_help_embed(), ephemeral=True)

# 음악 도움말 임베드 생성
def create_music_help_embed():
    embed = discord.Embed(
        title="🎵 음악 봇 명령어 목록 🎵",
        color=discord.Color.blue(),
        description="음악 봇을 이용하는 데 필요한 명령어들입니다."
    )
    
    # 기본 명령어
    basic_commands = [
        ("/join", "봇을 현재 음성 채널에 참여시킵니다."),
        ("/forcejoin", "봇이 다른 채널에 있어도 강제로 현재 채널로 이동시킵니다."),
        ("/play <URL>", "YouTube 링크로 음악을 재생합니다."),
        ("/playlist <URL>", "YouTube 플레이리스트의 곡들을 재생 목록에 추가합니다.")
    ]
    
    # 제어 명령어
    control_commands = [
        ("/stop", "현재 재생 중인 음악을 중지하고 재생 대기열을 비웁니다."),
        ("/skip", "현재 재생 중인 음악을 건너뜁니다."),
        ("/volume [0-100]", "음량을 설정합니다. 값을 입력하지 않으면 현재 음량을 표시합니다."),
        ("/nowplaying", "현재 재생 중인 곡을 표시합니다."),
        ("/queue", "현재 대기열에 있는 음악 목록을 보여줍니다.")
    ]
    
    # 기본 명령어 필드 추가
    embed.add_field(name="⏯️ 기본 명령어", value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in basic_commands]), inline=False)
    
    # 제어 명령어 필드 추가
    embed.add_field(name="🎛️ 제어 명령어", value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in control_commands]), inline=False)
    
    # 사용 방법 필드 추가
    usage = [
        "1. 음성 채널에 들어갑니다.",
        "2. `/join` 명령어로 봇을 음성 채널에 참여시킵니다.",
        "3. `/play <URL>` 명령어로 음악을 재생합니다.",
        "4. 필요한 경우 `/skip`으로 다음 곡으로 넘어가거나, `/stop`으로 재생을 중지할 수 있습니다."
    ]
    
    embed.add_field(name="📝 사용 방법", value="\n".join(usage), inline=False)
    
    embed.set_footer(text="문제가 있을 경우 관리자에게 문의하세요.")
    
    return embed

# 금칙어 게임 도움말 임베드 생성
def create_game_help_embed():
    embed = discord.Embed(
        title="🎮 금칙어 게임 명령어 목록 🎮",
        color=discord.Color.green(),
        description="금칙어 게임을 즐기기 위한 명령어들입니다."
    )
    
    # 게임 명령어
    game_commands = [
        ("/참가", "금칙어 게임에 참가합니다."),
        ("/시작", "금칙어 게임을 시작합니다. (최소 2명 이상 필요)"),
        ("/금칙어 <단어>", "배정받은 플레이어의 금칙어를 설정합니다."),
        ("/참가자", "현재 참가자 목록을 보여줍니다."),
        ("/종료", "게임을 종료합니다.")
    ]
    
    # 게임 규칙
    game_rules = [
        "1. 게임이 시작되면 각 플레이어는 다른 플레이어의 금칙어를 설정합니다.",
        "2. 각 플레이어는 자신의 금칙어를 모르기 때문에 주의해야 합니다.",
        "3. 금칙어를 사용한 플레이어는 자동으로 탈락합니다.",
        "4. 마지막까지 남은 플레이어가 승리합니다."
    ]
    
    # 명령어 필드 추가
    embed.add_field(name="🎮 게임 명령어", value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in game_commands]), inline=False)
    
    # 규칙 필드 추가
    embed.add_field(name="📋 게임 규칙", value="\n".join(game_rules), inline=False)
    
    embed.set_footer(text="즐거운 게임 되세요!")
    
    return embed

async def show_command_list(channel):
    """사용 가능한 명령어 목록을 보여줍니다."""
    embed = discord.Embed(
        title="🤖 봇 명령어 목록",
        description="사용 가능한 모든 명령어와 설명입니다.",
        color=discord.Color.blue()
    )
    
    # 음악 관련 명령어
    music_commands = [
        ("/join", "봇을 현재 음성 채널에 참여시킵니다."),
        ("/forcejoin", "봇이 다른 채널에 있어도 강제로 현재 채널로 이동시킵니다."),
        ("/play <URL>", "YouTube 링크로 음악을 재생합니다."),
        ("/playlist <URL>", "YouTube 플레이리스트의 곡들을 재생 목록에 추가합니다."),
        ("/stop", "현재 재생 중인 음악을 중지하고 재생 대기열을 비웁니다."),
        ("/skip", "현재 재생 중인 음악을 건너뜁니다."),
        ("/volume [0-100]", "음량을 설정합니다. 값을 입력하지 않으면 현재 음량을 표시합니다."),
        ("/nowplaying", "현재 재생 중인 곡을 표시합니다."),
        ("/queue", "현재 대기열에 있는 음악 목록을 보여줍니다."),
        ("/leave", "봇을 음성 채널에서 내보냅니다."),
        ("/search <검색어>", "YouTube에서 음악을 검색합니다.")
    ]
    
    # 금칙어 게임 관련 명령어
    game_commands = [
        ("/참가", "금칙어 게임에 참가합니다."),
        ("/시작", "금칙어 게임을 시작합니다. (최소 2명 이상 필요)"),
        ("/금칙어 <단어>", "배정받은 플레이어의 금칙어를 설정합니다."),
        ("/참가자", "현재 참가자 목록을 보여줍니다."),
        ("/종료", "게임을 종료합니다.")
    ]
    
    # 도움말 명령어
    help_commands = [
        ("/musichelp", "음악 봇 사용법을 자세히 보여줍니다."),
        ("/", "이 도움말을 표시합니다.")
    ]
    
    # 슬래시 명령어
    slash_commands = [
        ("/도움말", "사용 가능한 모든 명령어와 설명을 보여줍니다."),
        ("/음악도움말", "음악 봇 사용법을 자세히 보여줍니다."),
        ("/게임도움말", "금칙어 게임 사용법을 자세히 보여줍니다.")
    ]
    
    # 명령어 필드 추가
    embed.add_field(name="🎵 음악 명령어", value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in music_commands]), inline=False)
    embed.add_field(name="🎮 금칙어 게임 명령어", value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in game_commands]), inline=False)
    embed.add_field(name="❓ 도움말 명령어", value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in help_commands]), inline=False)
    embed.add_field(name="🔍 슬래시 명령어", value="\n".join([f"`{cmd}` - {desc}" for cmd, desc in slash_commands]), inline=False)
    
    embed.set_footer(text="명령어를 사용하려면 채팅창에 명령어를 입력하세요.")
    
    await channel.send(embed=embed)

# 음악 관련 슬래시 명령어
@bot.tree.command(name="join", description="봇을 현재 음성 채널에 참여시킵니다.")
async def slash_join(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    await join(ctx)

@bot.tree.command(name="forcejoin", description="봇이 다른 채널에 있어도 강제로 현재 채널로 이동시킵니다.")
async def slash_forcejoin(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    await forcejoin(ctx)

@bot.tree.command(name="play", description="YouTube 링크로 음악을 재생합니다.")
async def slash_play(interaction: discord.Interaction, url: str):
    ctx = await commands.Context.from_interaction(interaction)
    await play(ctx, url)

@bot.tree.command(name="playlist", description="YouTube 플레이리스트의 곡들을 재생 목록에 추가합니다.")
async def slash_playlist(interaction: discord.Interaction, url: str):
    ctx = await commands.Context.from_interaction(interaction)
    await playlist(ctx, url)

@bot.tree.command(name="stop", description="현재 재생 중인 음악을 중지하고 재생 대기열을 비웁니다.")
async def slash_stop(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    await stop(ctx)

@bot.tree.command(name="skip", description="현재 재생 중인 음악을 건너뜁니다.")
async def slash_skip(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    await skip(ctx)

@bot.tree.command(name="queue", description="현재 대기열에 있는 음악 목록을 보여줍니다.")
async def slash_queue(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    await queue(ctx)

@bot.tree.command(name="nowplaying", description="현재 재생 중인 곡을 표시합니다.")
async def slash_nowplaying(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    await nowplaying(ctx)

@bot.tree.command(name="volume", description="음량을 설정합니다. (0-100)")
async def slash_volume(interaction: discord.Interaction, volume: int = None):
    ctx = await commands.Context.from_interaction(interaction)
    await volume(ctx, volume)

@bot.tree.command(name="leave", description="봇을 음성 채널에서 내보냅니다.")
async def slash_leave(interaction: discord.Interaction):
    ctx = await commands.Context.from_interaction(interaction)
    await leave(ctx)

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN')) 