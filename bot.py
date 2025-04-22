import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
import re
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from datetime import timedelta, datetime
import pytz

# --- 건의함 채널 ID 저장 변수 ---
suggestion_input_channel_id = None
suggestion_output_channel_id = None
suggestion_mention_role_id = None # 맨션할 역할 ID 저장
# -----------------------------

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

# --- 운세 관련 상수 및 전역 변수 ---
ZODIAC_URLS = {
    "쥐": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%A5%90%EB%9D%A0%20%EC%9A%B4%EC%84%B8",
    "소": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%86%8C%EB%9D%A0%20%EC%9A%B4%EC%84%B8",
    "호랑이": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%ED%98%B8%EB%9E%91%EC%9D%B4%EB%9D%A0%20%EC%9A%B4%EC%84%B8",
    "토끼": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%ED%86%A0%EB%81%BC%EB%9D%A0%20%EC%9A%B4%EC%84%B8",
    "용": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%9A%A9%EB%9D%A0%20%EC%9A%B4%EC%84%B8", # '용따' 오타 수정
    "뱀": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EB%B1%80%EB%9D%A0%20%EC%9A%B4%EC%84%B8",
    "말": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EB%A7%90%EB%9D%A0%20%EC%9A%B4%EC%84%B8",
    "양": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%96%91%EB%9D%A0%20%EC%9A%B4%EC%84%B8",
    "원숭이": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%9B%90%EC%88%AD%EC%9D%B4%EB%9D%A0%20%EC%9A%B4%EC%84%B8",
    "닭": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EB%8B%AD%EB%9D%A0%20%EC%9A%B4%EC%84%B8",
    "개": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EA%B0%9C%EB%9D%A0%20%EC%9A%B4%EC%84%B8",
    "돼지": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EB%8F%BC%EC%A7%80%EB%9D%A0%20%EC%9A%B4%EC%84%B8"
}

STAR_SIGN_URLS = {
    "물병자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EB%AC%BC%EB%B3%91%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "물고기자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EB%AC%BC%EA%B3%A0%EA%B8%B0%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "양자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%96%91%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "황소자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%ED%99%A9%EC%86%8C%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "쌍둥이자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%8C%8D%EB%91%A5%EC%9D%B4%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "게자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EA%B2%8C%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "사자자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%82%AC%EC%9E%90%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "처녀자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%B2%98%EB%85%80%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "천칭자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%B2%9C%EC%B9%AD%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "전갈자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%A0%84%EA%B0%88%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "사수자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%82%AC%EC%88%98%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8",
    "염소자리": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&qvt=0&query=%EC%97%BC%EC%86%8C%EC%9E%90%EB%A6%AC%20%EC%9A%B4%EC%84%B8"
}

STAR_SIGN_DATES = {
    "물병자리": "(1월 20일 ~ 2월 18일)", "물고기자리": "(2월 19일 ~ 3월 20일)",
    "양자리": "(3월 21일 ~ 4월 19일)", "황소자리": "(4월 20일 ~ 5월 20일)",
    "쌍둥이자리": "(5월 21일 ~ 6월 21일)", "게자리": "(6월 22일 ~ 7월 22일)",
    "사자자리": "(7월 23일 ~ 8월 22일)", "처녀자리": "(8월 23일 ~ 9월 23일)",
    "천칭자리": "(9월 24일 ~ 10월 22일)", "전갈자리": "(10월 23일 ~ 11월 22일)",
    "사수자리": "(11월 23일 ~ 12월 24일)", "염소자리": "(12월 25일 ~ 1월 19일)"
}

# 사용자 입력과 표준 띠 이름 매핑 (추가)
ZODIAC_NAME_MAP = {
    "쥐": "쥐", "쥐띠": "쥐",
    "소": "소", "소띠": "소",
    "호랑이": "호랑이", "호랑이띠": "호랑이", "호랑": "호랑이",
    "토끼": "토끼", "토끼띠": "토끼",
    "용": "용", "용띠": "용",
    "뱀": "뱀", "뱀띠": "뱀",
    "말": "말", "말띠": "말",
    "양": "양", "양띠": "양",
    "원숭이": "원숭이", "원숭이띠": "원숭이", "원숭": "원숭이",
    "닭": "닭", "닭띠": "닭",
    "개": "개", "개띠": "개",
    "돼지": "돼지", "돼지띠": "돼지"
}

zodiac_horoscopes = {}
star_sign_horoscopes = {}
is_updating = False # 업데이트 중복 방지 플래그

# --- 웹 크롤링 및 파싱 함수 ---
async def fetch_fortune(url: str):
    """ 지정된 URL에서 HTML 내용을 비동기적으로 가져옵니다. """
    loop = asyncio.get_event_loop()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    try:
        response = await loop.run_in_executor(None, lambda: requests.get(url, headers=headers))
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

async def parse_zodiac_fortune(html_content: str) -> str:
    """ HTML 내용에서 띠별 운세 정보를 파싱합니다. (연도별) """
    if not html_content:
        return "운세 정보를 가져올 수 없습니다."

    soup = BeautifulSoup(html_content, 'html.parser')
    fortune_dl = soup.select_one('._resultPanel dl.lst_infor._cs_fortune_list')

    if not fortune_dl:
        print("띠별 운세 dl 태그(lst_infor _cs_fortune_list)를 찾을 수 없습니다.")
        fortune_dl = soup.select_one('._resultPanel dl._cs_fortune_list')
        if not fortune_dl:
             print("대체 띠별 운세 dl 태그(_cs_fortune_list)도 찾을 수 없습니다.")
             return "운세 정보를 찾을 수 없습니다. (dl 구조 확인 필요)"

    fortune_items = fortune_dl.find_all('div', recursive=False)

    if not fortune_items:
         print("띠별 운세 dl 태그 내부에 div 항목들을 찾을 수 없습니다.")
         dt_items = fortune_dl.find_all('dt', recursive=False)
         dd_items = fortune_dl.find_all('dd', recursive=False)
         if len(dt_items) == len(dd_items) and len(dt_items) > 0:
             parsed_fortunes = []
             for dt_tag, dd_tag in zip(dt_items, dd_items):
                 year_text = dt_tag.get_text(strip=True).replace('년생', '').strip()
                 description = dd_tag.get_text(strip=True).replace("총운", "", 1).strip()
                 if year_text and description:
                      parsed_fortunes.append(f"{year_text} : {description}")
             if parsed_fortunes:
                 print("dl 바로 아래 dt/dd 구조에서 파싱 성공.")
                 return "\n".join(parsed_fortunes)

         return "운세 정보를 찾을 수 없습니다. (div 구조 확인 필요)"

    parsed_fortunes = []
    for item_div in fortune_items:
        year_tag = item_div.find('dt')
        desc_tag = item_div.find('dd')

        if year_tag and desc_tag:
            year_em = year_tag.find('em')
            year_text = year_em.get_text(strip=True) if year_em else year_tag.get_text(strip=True)
            year_text = year_text.replace('년생', '').strip()

            description = desc_tag.get_text(strip=True).replace("총운", "", 1).strip()
            if year_text and description:
                 parsed_fortunes.append(f"{year_text} : {description}")
        else:
            print(f"div 항목에서 dt 또는 dd 태그를 찾을 수 없습니다: {item_div}")

    if not parsed_fortunes:
        print("띠별 운세 div 구조 내에서 유효한 내용을 파싱하지 못했습니다.")
        return "운세 정보를 파싱할 수 없습니다."

    return "\n".join(parsed_fortunes)

async def parse_star_sign_fortune(html_content: str) -> str:
    """ HTML 내용에서 별자리 운세 정보를 파싱합니다. """
    if not html_content:
        return "운세 정보를 가져올 수 없습니다."

    soup = BeautifulSoup(html_content, 'html.parser')
    fortune_text_element = soup.select_one('._resultPanel p.text._cs_fortune_text')

    if not fortune_text_element:
        fortune_text_element = soup.select_one('._resultPanel ._cs_fortune_text')
        if not fortune_text_element:
            print("별자리 운세 텍스트 요소(p.text._cs_fortune_text 또는 ._cs_fortune_text)를 찾을 수 없습니다.")
            return "운세 정보를 찾을 수 없습니다. (p 또는 div 구조 확인 필요)"

    raw_fortune = fortune_text_element.get_text(separator='\n', strip=True)
    cleaned_fortune = re.sub(r"^(오늘\s*)?\d{4}\.\d{2}\.\d{2}\.?(\s*[가-힣]{1}요일)?\s*(\n)?", "", raw_fortune, count=1)
    cleaned_fortune = re.sub(r"^\d{1,2}월\s*\d{1,2}일\s*~\s*\d{1,2}월\s*\d{1,2}일\s*(\n)?", "", cleaned_fortune, count=1).strip()
    cleaned_fortune = cleaned_fortune.replace("총운", "").strip()

    if not cleaned_fortune:
        print(f"별자리 운세 파싱 후 내용이 비어 있습니다. 원본: {raw_fortune}")
        return "운세 내용이 비어 있습니다."

    return cleaned_fortune

async def update_all_horoscopes():
    """ 모든 띠와 별자리의 운세 정보를 크롤링하고 파싱하여 업데이트합니다. """
    global zodiac_horoscopes, star_sign_horoscopes, is_updating
    if is_updating:
        print("이미 운세 업데이트가 진행 중입니다.")
        return False

    is_updating = True
    print("운세 정보 업데이트 시작...")

    zodiac_tasks = []
    star_sign_tasks = []
    request_delay = 0.5

    for name, url in ZODIAC_URLS.items():
        zodiac_tasks.append(asyncio.create_task(fetch_fortune(url), name=f"zodiac_{name}"))
        await asyncio.sleep(request_delay)

    for name, url in STAR_SIGN_URLS.items():
        star_sign_tasks.append(asyncio.create_task(fetch_fortune(url), name=f"starsign_{name}"))
        await asyncio.sleep(request_delay)

    print("모든 요청 생성 완료, HTML 가져오기 시작...")
    zodiac_html_results = await asyncio.gather(*zodiac_tasks, return_exceptions=True)
    star_sign_html_results = await asyncio.gather(*star_sign_tasks, return_exceptions=True)
    print("HTML 가져오기 완료, 파싱 시작...")

    new_zodiac_horoscopes = {}
    new_star_sign_horoscopes = {}

    zodiac_names = list(ZODIAC_URLS.keys())
    for i, result in enumerate(zodiac_html_results):
        name = zodiac_names[i]
        if isinstance(result, Exception):
            print(f"{name}띠 운세 HTML 가져오기 실패: {result}")
            new_zodiac_horoscopes[name] = "오류: 운세 정보를 가져올 수 없습니다."
        elif result:
            parsed_fortune = await parse_zodiac_fortune(result)
            title = f"**[{name}띠]**"
            new_zodiac_horoscopes[name] = f"{title}\n{parsed_fortune}"
        else:
             new_zodiac_horoscopes[name] = "오류: 운세 정보를 가져올 수 없습니다."

    star_sign_names = list(STAR_SIGN_URLS.keys())
    for i, result in enumerate(star_sign_html_results):
        name = star_sign_names[i]
        if isinstance(result, Exception):
            print(f"{name} 운세 HTML 가져오기 실패: {result}")
            new_star_sign_horoscopes[name] = "오류: 운세 정보를 가져올 수 없습니다."
        elif result:
            parsed_fortune = await parse_star_sign_fortune(result)
            date_range = STAR_SIGN_DATES.get(name, "")
            title = f"**[{name}]** {date_range}"
            new_star_sign_horoscopes[name] = f"{title}\n{parsed_fortune}"
        else:
            new_star_sign_horoscopes[name] = "오류: 운세 정보를 가져올 수 없습니다."

    zodiac_horoscopes = new_zodiac_horoscopes
    star_sign_horoscopes = new_star_sign_horoscopes

    is_updating = False
    print("운세 정보 업데이트 완료.")
    return True

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

async def ensure_voice(interaction: discord.Interaction) -> Optional[discord.VoiceClient]:
    """
    명령어 사용자가 음성 채널에 있는지 확인하고,
    봇이 해당 채널에 연결되도록 보장합니다.
    연결 성공 시 VoiceClient 객체를, 실패 시 None을 반환합니다.
    """
    if not interaction.user.voice:
        # defer 전에 응답해야 함
        if not interaction.response.is_done():
             await interaction.response.send_message("먼저 음성 채널에 참여해주세요.", ephemeral=True)
        else:
             await interaction.followup.send("먼저 음성 채널에 참여해주세요.", ephemeral=True)
        return None

    user_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    if voice_client is None:
        try:
            print(f"Connecting to voice channel: {user_channel.name}")
            vc = await user_channel.connect()
            player.voice_client = vc
            print(f"Connected successfully.")
            return vc
        except Exception as e:
            print(f"Error connecting to voice channel: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"음성 채널에 연결하는 중 오류 발생: {e}", ephemeral=True)
            else:
                 await interaction.followup.send(f"음성 채널에 연결하는 중 오류 발생: {e}", ephemeral=True)
            return None
    elif voice_client.channel != user_channel:
        try:
            print(f"Moving to voice channel: {user_channel.name}")
            await voice_client.move_to(user_channel)
            # player.voice_client는 move_to 후에도 동일 객체를 참조하므로 업데이트 불필요
            print(f"Moved successfully.")
            return voice_client
        except Exception as e:
            print(f"Error moving to voice channel: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"음성 채널 이동 중 오류 발생: {e}", ephemeral=True)
            else:
                 await interaction.followup.send(f"음성 채널 이동 중 오류 발생: {e}", ephemeral=True)
            return None
    else:
        # 이미 올바른 채널에 연결되어 있음
        print(f"Already in the correct voice channel: {user_channel.name}")
        return voice_client


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

    # 봇 시작 시 운세 정보 업데이트 실행 (추가)
    await update_all_horoscopes()

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

# --- 운세 관련 슬래시 명령어 ---

@bot.tree.command(name="띠별운세", description="지정한 띠의 오늘 운세를 보여줍니다.")
@app_commands.describe(띠_이름="운세를 알고 싶은 띠 이름을 입력하세요 (예: 토끼, 호랑, 돼지띠)")
async def slash_zodiac_fortune(interaction: discord.Interaction, 띠_이름: str):
    """ 사용자가 요청한 띠의 운세를 찾아서 응답합니다. """
    # 사용자 입력을 표준 띠 이름으로 변환
    canonical_name = ZODIAC_NAME_MAP.get(띠_이름.strip())

    # 유효성 검사
    if not canonical_name:
        # ZODIAC_URLS의 키 목록을 유효한 옵션으로 제시
        valid_zodiacs = ", ".join(ZODIAC_URLS.keys())
        await interaction.response.send_message(f"'{띠_이름}'은(는) 유효한 띠 이름이 아닙니다. 다음 중에서 선택해주세요: {valid_zodiacs}", ephemeral=True)
        return

    # 표준 이름으로 운세 정보 가져오기 (이미 **[띠이름]** 형식으로 저장되어 있음)
    fortune = zodiac_horoscopes.get(canonical_name, "아직 운세 정보가 업데이트되지 않았거나 가져오는 데 실패했습니다.")
    if len(fortune) > 1990:
        fortune = fortune[:1990] + "... (내용이 너무 깁니다)"

    await interaction.response.send_message(fortune, ephemeral=False)

@bot.tree.command(name="별자리운세", description="지정한 별자리의 오늘 운세를 보여줍니다.")
@app_commands.describe(별자리_이름="운세를 알고 싶은 별자리 이름을 입력하세요 (예: 사자자리 또는 사자)")
async def slash_star_sign_fortune(interaction: discord.Interaction, 별자리_이름: str):
    """ 사용자가 요청한 별자리의 운세를 찾아서 응답합니다. """
    # 입력값 정규화 ("자리" 추가)
    normalized_name = 별자리_이름.strip()
    if not normalized_name.endswith("자리"):
        normalized_name += "자리"

    # 유효성 검사
    if normalized_name not in STAR_SIGN_URLS:
         valid_signs = ", ".join(STAR_SIGN_URLS.keys())
         await interaction.response.send_message(f"'{별자리_이름}'은(는) 유효한 별자리 이름이 아닙니다. 다음 중에서 선택해주세요: {valid_signs}", ephemeral=True)
         return

    # 정규화된 이름으로 운세 정보 가져오기
    fortune_text = star_sign_horoscopes.get(normalized_name, "아직 운세 정보가 업데이트되지 않았거나 가져오는 데 실패했습니다.")

    # 메시지 길이 제한 확인
    if len(fortune_text) > 1990:
        fortune_text = fortune_text[:1990] + "... (내용이 너무 깁니다)"

    # 제목에서 날짜 범위 가져오기 (기존 로직 활용)
    # update_all_horoscopes 에서 이미 제목에 날짜를 포함시킴
    # fortune_text 는 제목 + 내용 형태이므로 그대로 사용

    await interaction.response.send_message(fortune_text, ephemeral=False)

@bot.tree.command(name="운세업데이트", description="웹에서 최신 운세 정보를 가져와 업데이트합니다.")
# @app_commands.checks.has_permissions(administrator=True) # 관리자 권한 필요 시 주석 해제
async def slash_update_horoscopes_command(interaction: discord.Interaction):
    """ '/운세업데이트' 명령어로 웹 크롤링 및 파싱을 수행합니다. """
    if is_updating:
        await interaction.response.send_message("현재 운세 정보를 업데이트하는 중입니다. 잠시 후 다시 시도해주세요.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True) # 처리 중 메시지 표시
    success = await update_all_horoscopes() # 실제 업데이트 함수 호출
    if success:
        await interaction.followup.send("운세 정보 업데이트를 완료했습니다.", ephemeral=True)
    else:
        await interaction.followup.send("운세 정보 업데이트 중 오류가 발생했거나 이미 진행 중입니다.", ephemeral=True)

# --- 기존 슬래시 명령어 정의 (음악, 게임 등) ---

@bot.tree.command(name="검색", description="YouTube에서 음악을 검색합니다.")
async def slash_search(interaction: discord.Interaction, query: str):
    """YouTube에서 음악을 검색하고 선택한 곡을 재생합니다."""
    # defer()는 ensure_voice 전에 호출되면 안 됨 (ensure_voice에서 응답 필요할 수 있음)
    # voice_client = await ensure_voice(interaction)
    # if not voice_client:
    #     return # 오류 메시지는 ensure_voice에서 처리

    # 먼저 음성 채널 참여 시도
    if not interaction.user.voice:
        await interaction.response.send_message("음성 채널에 먼저 입장해주세요!", ephemeral=True)
        return

    # 검색 전에 defer
    await interaction.response.defer()

    try:
        # 검색 옵션 설정 (기존 유지)
        ydl_opts_search = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch5',  # 상위 5개 결과만 가져오기
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True, # 검색 시에는 빠르게 정보만
            'socket_timeout': 30,
            'retries': 5,
            'buffersize': 16384
        }

        # 비동기로 검색 실행
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts_search) as ydl:
            try:
                print(f"Searching YouTube for: {query}")
                search_results = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch5:{query}", download=False))
                print(f"Search complete.")
            except Exception as e:
                print(f"yt-dlp search error: {e}")
                await interaction.followup.send(f"검색 중 오류가 발생했습니다: {str(e)}", ephemeral=True)
                return

        if not search_results or 'entries' not in search_results:
            await interaction.followup.send("검색 결과를 찾을 수 없습니다.", ephemeral=True)
            return

        # 검색 결과 표시 (기존 유지)
        embed = discord.Embed(
            title="🎵 검색 결과",
            description="재생할 곡의 번호를 입력해주세요 (1-5)\n취소하려면 '취소'를 입력하세요.",
            color=discord.Color.blue()
        )

        valid_entries = [entry for entry in search_results['entries'] if entry] # None 제거
        if not valid_entries:
            await interaction.followup.send("유효한 검색 결과를 찾을 수 없습니다.", ephemeral=True)
            return

        for i, entry in enumerate(valid_entries, 1):
            title = entry.get('title', '제목 없음')
            duration = entry.get('duration')
            url = f"https://www.youtube.com/watch?v={entry['id']}"

            duration_str = "알 수 없음"
            if duration:
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

        # 사용자 선택 대기 (기존 유지)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)

            if msg.content.lower() == '취소':
                await msg.delete() # 사용자 메시지 삭제
                await search_msg.edit(content="검색이 취소되었습니다.", embed=None)
                return

            try:
                choice = int(msg.content)
                if not 1 <= choice <= len(valid_entries):
                    await msg.delete() # 사용자 메시지 삭제
                    await interaction.followup.send(f"올바른 번호를 입력해주세요 (1-{len(valid_entries)}).", ephemeral=True, delete_after=5)
                    await search_msg.delete() # 검색 결과 메시지 삭제
                    return
            except ValueError:
                await msg.delete()
                await interaction.followup.send(f"올바른 번호를 입력해주세요 (1-{len(valid_entries)}).", ephemeral=True, delete_after=5)
                await search_msg.delete()
                return

            await msg.delete() # 유효한 선택 후 사용자 메시지 삭제
            selected = valid_entries[choice - 1]
            selected_url = f"https://www.youtube.com/watch?v={selected['id']}"
            selected_title = selected.get('title', '선택된 곡')

            # --- 음성 채널 참여 확인 및 연결 --- #
            print(f"Ensuring voice connection for {interaction.user.name} after selecting '{selected_title}'")
            voice_client = await ensure_voice(interaction)
            if not voice_client:
                # ensure_voice 내부에서 오류 메시지 전송됨
                await search_msg.edit(content="음성 채널 연결 실패. 다시 시도해주세요.", embed=None)
                return
            print(f"Voice connection ensured/established.")
            # --- 음성 채널 참여 확인 끝 --- #

            await search_msg.edit(content=f"⏳ `{selected_title}` 정보 가져오는 중...", embed=None)

            # --- 선택된 곡 정보 다시 가져오기 (스트림 URL 포함) --- #
            ydl_opts_play = ytdl_format_options.copy()
            ydl_opts_play['noplaylist'] = True # 확실하게 단일 곡만 처리
            with yt_dlp.YoutubeDL(ydl_opts_play) as ydl:
                try:
                    print(f"Fetching full info for: {selected_url}")
                    info = await loop.run_in_executor(None, lambda: ydl.extract_info(selected_url, download=False))
                    print(f"Full info fetched.")
                except Exception as e:
                    print(f"yt-dlp play info fetch error: {e}")
                    await search_msg.edit(content=f"오류: `{selected_title}`의 정보를 가져올 수 없습니다.", embed=None)
                    return

            stream_url = info.get('url')
            if not stream_url:
                 await search_msg.edit(content=f"오류: `{selected_title}`의 스트리밍 URL을 찾을 수 없습니다.", embed=None)
                 return
            # --- 정보 가져오기 끝 --- #

            # --- 큐에 추가 및 재생 시작 --- #
            song_data = {
                'url': stream_url, # 실제 스트림 URL 사용
                'title': info.get('title', selected_title),
                'webpage_url': info.get('webpage_url', selected_url),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'requester': interaction.user.mention
            }

            player.queue.append(song_data)
            print(f"Added '{song_data['title']}' to queue. Queue size: {len(player.queue)}")
            await search_msg.edit(content=f"✅ `{song_data['title']}`을(를) 대기열에 추가했습니다.", embed=None)

            if not player.is_playing:
                print("Player not playing, starting playback.")
                await player.play_next()
            # --- 큐 추가 및 재생 끝 --- #

        except asyncio.TimeoutError:
            await search_msg.edit(content="시간 초과. 다시 시도해주세요.", embed=None)
        except Exception as e:
             print(f"Error during song selection/processing: {e}")
             try:
                 # 에러 발생 시 defer된 응답 처리
                 await interaction.followup.send(f"곡 처리 중 오류 발생: {e}", ephemeral=True)
                 await search_msg.delete() # 오류 시 검색 메시지 삭제 시도
             except discord.NotFound:
                 pass # 이미 삭제되었거나 다른 오류로 찾을 수 없음
             except Exception as inner_e:
                 print(f"Error sending followup error message: {inner_e}")

    except Exception as e:
        print(f"Unhandled error in slash_search: {e}")
        try:
            # 최상위 레벨 에러 처리 (defer 후)
            await interaction.followup.send(f"명령어 처리 중 심각한 오류 발생: {e}", ephemeral=True)
        except Exception as final_e:
            print(f"Failed to send final error message: {final_e}")


# 음악 관련 슬래시 명령어 (직접 로직 구현 방식으로 변경)
@bot.tree.command(name="참여", description="봇을 현재 음성 채널에 참여시킵니다.")
async def slash_join(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    voice_client = await ensure_voice(interaction)
    if voice_client:
        await interaction.followup.send(f"{voice_client.channel.mention} 채널에 참여했습니다.")
    # 실패 메시지는 ensure_voice에서 처리

@bot.tree.command(name="강제참여", description="봇이 다른 채널에 있어도 강제로 현재 채널로 이동시킵니다.")
async def slash_forcejoin(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    voice_client = await ensure_voice(interaction) # ensure_voice가 이동까지 처리
    if voice_client:
        await interaction.followup.send(f"{voice_client.channel.mention} 채널로 이동했습니다.")
    # 실패 메시지는 ensure_voice에서 처리

@bot.tree.command(name="재생", description="YouTube 링크로 음악을 재생합니다.")
@app_commands.describe(url="재생할 YouTube 영상 또는 재생목록 URL")
async def slash_play(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    voice_client = await ensure_voice(interaction)
    if not voice_client:
        return

    loop = asyncio.get_event_loop()
    try:
        # 플레이리스트인지 단일 곡인지 확인 필요 -> yt-dlp가 처리하도록 맡김
        # 단, 플레이리스트 처리를 위한 별도 옵션 사용 여부 결정 필요
        is_playlist = 'list=' in url

        ydl_opts_play = ytdl_format_options.copy()
        # ydl_opts_play['noplaylist'] = not is_playlist # 자동으로 처리하도록 둘 수도 있음

        print(f"Fetching info for URL: {url} (Playlist: {is_playlist})")
        with yt_dlp.YoutubeDL(ydl_opts_play) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
        print(f"Info fetched for {url}")

        entries_to_add = []
        if '_type' in info and info['_type'] == 'playlist':
            entries_to_add = info.get('entries', [])
            playlist_title = info.get('title', '알 수 없는 플레이리스트')
            await interaction.followup.send(f" Playlist `{playlist_title}` ({len(entries_to_add)} 곡) 정보를 가져왔습니다. 대기열에 추가 중...")
        else:
            entries_to_add = [info] # 단일 곡도 리스트로 처리

        added_count = 0
        for entry in entries_to_add:
            if not entry:
                 print("Skipping invalid entry in playlist/song.")
                 continue

            stream_url = entry.get('url')
            if not stream_url:
                 # 평탄화된(flat) 결과가 아니라면 보통 url 필드가 존재함
                 # 만약 없다면 다시 시도하거나 건너뛰기
                 print(f"Warning: No stream URL found for entry {entry.get('id') or 'N/A'}. Title: {entry.get('title', 'N/A')}")
                 # TODO: 필요 시 extract_flat=False로 다시 정보 가져오기 시도?
                 continue

            song_data = {
                'url': stream_url,
                'title': entry.get('title', '제목 없음'),
                'webpage_url': entry.get('webpage_url', url if not is_playlist else entry.get('url')), # 플레이리스트 항목 url
                'thumbnail': entry.get('thumbnail'),
                'duration': entry.get('duration'),
                'requester': interaction.user.mention
            }
            player.queue.append(song_data)
            added_count += 1

        if added_count > 0:
            queue_msg = f"✅ {added_count}개의 곡을 대기열에 추가했습니다."
            if not is_playlist and added_count == 1:
                queue_msg = f"✅ `{entries_to_add[0].get('title', '곡')}`을(를) 대기열에 추가했습니다."

            # 기존 메시지가 있다면 수정, 없다면 새로 전송
            try:
                await interaction.edit_original_response(content=queue_msg)
            except discord.NotFound:
                 await interaction.followup.send(queue_msg)

            if not player.is_playing:
                print("Player not playing, starting playback after adding song(s).")
                await player.play_next()
        else:
            await interaction.followup.send("⚠️ 대기열에 추가할 유효한 곡을 찾지 못했습니다.", ephemeral=True)

    except yt_dlp.utils.DownloadError as e:
         await interaction.followup.send(f"오류: URL 정보를 가져올 수 없습니다. 링크가 올바른지 확인해주세요. ({e})", ephemeral=True)
    except Exception as e:
        print(f"Error in slash_play: {e}")
        try:
            await interaction.followup.send(f"음악 재생 중 오류 발생: {e}", ephemeral=True)
        except discord.NotFound:
             # 이미 다른 메시지로 응답했을 수 있음
             pass
        except Exception as final_e:
             print(f"Failed to send final error message in slash_play: {final_e}")


@bot.tree.command(name="플레이리스트", description="YouTube 플레이리스트의 곡들을 재생 목록에 추가합니다.")
@app_commands.describe(url="재생할 YouTube 플레이리스트 URL")
async def slash_playlist(interaction: discord.Interaction, url: str):
    # 실제로는 /재생 명령어가 플레이리스트 처리 로직을 포함하도록 통합함
    # 사용성 측면에서는 별도 명령어가 더 명확할 수 있으나, 코드 중복을 줄이기 위해 통합
    # 여기서는 /재생을 호출하도록 간단히 처리하거나, 동일 로직 복사 가능
    await interaction.response.send_message("플레이리스트 처리는 `/재생` 명령어를 이용해주세요.", ephemeral=True)
    # 또는:
    # await slash_play(interaction, url) # slash_play 함수 직접 호출 (주의: defer 중복 등 문제 소지)


@bot.tree.command(name="중지", description="현재 재생 중인 음악을 중지하고 재생 대기열을 비웁니다.")
async def slash_stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message("봇이 음성 채널에 없습니다.", ephemeral=True)
        return

    if not player.is_playing and not player.queue:
        await interaction.response.send_message("재생 중인 곡이나 대기열이 없습니다.", ephemeral=True)
        return

    player.queue.clear()
    player.is_playing = False # play_next 콜백 전에 상태 변경
    player.current = None
    voice_client.stop() # stop()이 after 콜백을 트리거할 수 있으므로 is_playing 먼저 설정

    await interaction.response.send_message("⏹️ 재생을 중지하고 대기열을 비웠습니다.")
    print(f"Playback stopped and queue cleared by {interaction.user.name}")

@bot.tree.command(name="스킵", description="현재 재생 중인 음악을 건너뜁니다.")
async def slash_skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if not voice_client or not voice_client.is_playing():
        await interaction.response.send_message("현재 재생 중인 곡이 없습니다.", ephemeral=True)
        return

    # player.is_playing = False # stop() 후 after 콜백이 처리
    voice_client.stop() # after 콜백에서 play_next 호출하여 다음 곡 재생
    await interaction.response.send_message("⏭️ 현재 곡을 건너뛰었습니다.")
    print(f"Song skipped by {interaction.user.name}")

@bot.tree.command(name="대기열", description="현재 대기열에 있는 음악 목록을 보여줍니다.")
async def slash_queue(interaction: discord.Interaction):
    if not player.queue:
        await interaction.response.send_message("📭 대기열이 비어있습니다.", ephemeral=True)
        return

    embed = discord.Embed(title="🎶 재생 대기열", color=discord.Color.purple())
    queue_list = []
    for i, song in enumerate(player.queue[:10], 1): # 최대 10개 표시
        title = song.get('title', '제목 없음')
        requester = song.get('requester', '알 수 없음')
        queue_list.append(f"`{i}.` {title} (신청자: {requester})")

    embed.description = "\n".join(queue_list)
    if len(player.queue) > 10:
        embed.set_footer(text=f"... 외 {len(player.queue) - 10} 곡")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="현재곡", description="현재 재생 중인 곡을 표시합니다.")
async def slash_nowplaying(interaction: discord.Interaction):
    if not player.is_playing or not player.current:
        await interaction.response.send_message("현재 재생 중인 곡이 없습니다.", ephemeral=True)
        return

    song = player.current
    embed = discord.Embed(title="▶️ 현재 재생 중", color=discord.Color.green())
    title = song.get('title', '제목 없음')
    url = song.get('webpage_url', 'URL 없음')
    thumbnail = song.get('thumbnail')
    requester = song.get('requester', '알 수 없음')
    duration = song.get('duration')

    embed.description = f"[{title}]({url})"
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    duration_str = "알 수 없음"
    if duration:
        # 진행률 표시 (voice_client.source에서 현재 위치 가져오기 - 복잡할 수 있음)
        # 우선 총 길이만 표시
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        duration_str = f"{minutes}:{seconds:02d}"

    embed.add_field(name="길이", value=duration_str, inline=True)
    embed.add_field(name="신청자", value=requester, inline=True)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="음량", description="음량을 설정합니다. (0-100, 기본 50)")
@app_commands.describe(value="설정할 음량 값 (0~100)")
async def slash_volume(interaction: discord.Interaction, value: Optional[int] = None):
    voice_client = interaction.guild.voice_client

    if value is None:
        current_volume = int(player.volume * 100)
        await interaction.response.send_message(f"🔊 현재 음량: {current_volume}%", ephemeral=True)
        return

    if not 0 <= value <= 100:
        await interaction.response.send_message("음량은 0부터 100 사이의 값으로 입력해주세요.", ephemeral=True)
        return

    player.volume = value / 100.0
    print(f"Volume set to {value}% by {interaction.user.name}")

    if voice_client and voice_client.source:
        # 현재 재생 중인 소스의 볼륨 즉시 변경
        if isinstance(voice_client.source, discord.PCMVolumeTransformer):
             voice_client.source.volume = player.volume
             print("Applied volume change to current source.")
        else:
             print("Warning: Could not apply volume change to current source (not PCMVolumeTransformer).")

    await interaction.response.send_message(f"🔊 음량을 {value}%로 설정했습니다.")

@bot.tree.command(name="떠나기", description="봇을 음성 채널에서 내보냅니다.")
async def slash_leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message("봇이 음성 채널에 없습니다.", ephemeral=True)
        return

    await slash_stop(interaction) # 떠나기 전에 재생 중지 및 큐 비우기
    await voice_client.disconnect()
    player.voice_client = None # voice_client 참조 제거

    # slash_stop에서 이미 메시지를 보냈으므로 추가 응답은 불필요하거나 수정 필요
    # await interaction.followup.send("음성 채널을 떠났습니다.") # slash_stop 응답과 충돌 가능성
    print(f"Bot disconnected from voice channel by {interaction.user.name}")


@bot.tree.command(name="자기소개", description="자신의 정보를 등록하고 역할을 받습니다. 특정 채널에서만 사용 가능합니다.")
@app_commands.describe(
    닉네임="사용할 닉네임을 입력하세요.",
    성별="성별을 입력하세요 (예: 남, 여, 비공개).",
    나이="나이를 입력하세요 (예: 01, 25, 01년생, 20대).",
    플레이_하는_게임="주로 플레이하는 게임을 입력하세요.",
    자기소개="자신을 소개하는 간단한 메시지를 입력하세요."
)
async def slash_self_introduction(interaction: discord.Interaction, 닉네임: str, 성별: str, 나이: str, 플레이_하는_게임: str , 자기소개: str,):
    """ 사용자의 자기소개를 등록하고 역할들을 부여합니다. """

    member = interaction.user
    guild = interaction.guild

    if not isinstance(member, discord.Member):
         await interaction.response.send_message("서버 멤버 정보를 가져올 수 없습니다. 서버 내에서 명령어를 실행했는지 확인해주세요.", ephemeral=True)
         return

    if not guild:
        await interaction.response.send_message("서버 내에서만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return

    # --- 응답 지연 처리 ---
    print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] User {interaction.user.name} triggered /자기소개. Deferring...")
    await interaction.response.defer(ephemeral=False)
    print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Deferred successfully for {interaction.user.name}.")

    # --- 역할 찾기, 생성, 부여 (여러 역할 처리) ---
    role_names = ["자기소개 완료","Disboard"] # 부여할 역할 이름 목록
    roles_to_assign = []
    role_messages = [] # 역할 관련 메시지를 저장할 리스트 (현재는 임베드에 표시 안 함)

    for role_name in role_names:
        role = discord.utils.get(guild.roles, name=role_name)
        role_found_or_created = False

        # --- 역할 찾기 또는 생성 시도 ---
        if not role:
            role_messages.append(f"ℹ️ '{role_name}' 역할을 찾을 수 없습니다.")
            if not guild.me.guild_permissions.manage_roles:
                 role_messages.append(f"    ⚠️ **생성 불가:** 봇에게 '역할 관리' 권한 부족")
            else:
                try:
                    print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Role '{role_name}' not found for {member.name}. Attempting to create...")
                    role = await guild.create_role(name=role_name, reason=f"{role_name} 역할 자동 생성")
                    print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Role '{role_name}' created successfully for {member.name}.")
                    role_messages.append(f"    ✅ '{role_name}' 역할 생성됨.")
                    role_found_or_created = True
                except discord.Forbidden:
                    role_messages.append(f"    ⚠️ **생성 실패:** 권한 부족")
                except discord.HTTPException as e:
                    role_messages.append(f"    ⚠️ **생성 실패:** API 오류 ({e})")
                except Exception as e:
                     role_messages.append(f"    ⚠️ **생성 실패:** 알 수 없는 오류 ({e})")
        else:
            role_found_or_created = True

        # --- 역할 부여 시도 (역할이 존재하거나 성공적으로 생성된 경우) ---
        if role and role_found_or_created:
            can_assign_role = True
            if not guild.me.guild_permissions.manage_roles:
                 role_messages.append(f"    ⚠️ **'{role_name}' 부여 불가:** 봇에게 '역할 관리' 권한 없음")
                 can_assign_role = False
            elif guild.me.top_role <= role:
                 role_messages.append(f"    ⚠️ **'{role_name}' 부여 불가:** 봇 역할 순위 낮음 ({guild.me.top_role.name} <= {role.name})")
                 can_assign_role = False

            if can_assign_role:
                # 역할 부여 목록에 추가 (이미 가지고 있어도 괜찮음)
                roles_to_assign.append(role)
                if role in member.roles:
                    role_messages.append(f"    ℹ️ '{role_name}' 역할 이미 보유 중.")
                # else: # 부여 예정 메시지는 생략
                #     role_messages.append(f"    ⏳ '{role_name}' 역할 부여 예정.")

    # --- 모든 역할을 한 번에 부여 --- (API 호출 줄이기)
    if roles_to_assign:
        try:
            assigned_names = ', '.join([r.name for r in roles_to_assign]) # 로그를 위해 이름 미리 준비
            print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Attempting to add roles [{assigned_names}] to {member.name}({member.id})...")
            await member.add_roles(*roles_to_assign, reason="자기소개 완료 (다중 역할 부여)")
            # assigned_names = ', '.join([r.name for r in roles_to_assign]) # 위에서 이미 정의함
            role_messages.append(f"✅ 역할 부여 시도 완료: {assigned_names}")

            # --- 역할 부여 성공 로그 추가 ---
            now_kst = datetime.now(pytz.timezone('Asia/Seoul')) # KST 시간 가져오기
            log_message = f"[{now_kst.strftime('%Y-%m-%d %H:%M:%S KST')}] 역할 부여 성공: 사용자 {member.name}({member.id}) 에게 {assigned_names} 역할을 부여했습니다."
            print(log_message)
            # --- 로그 추가 끝 ---

            # --- 닉네임 변경 로직 추가 ---
            new_nickname = f"{닉네임} {성별} {나이}"
            print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Preparing to change nickname for {member.name} to '{new_nickname}'")
            if len(new_nickname) > 32:
                print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}]  ⚠️ Warning: Generated nickname '{new_nickname}' exceeds 32 characters. It will be truncated.")
                new_nickname = new_nickname[:32] # 32자로 자르기

            can_change_nickname = True
            if not guild.me.guild_permissions.manage_nicknames:
                print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}]  ⚠️ Nickname change failed for {member.name}: Bot lacks 'Manage Nicknames' permission.")
                role_messages.append("닉네임 변경 실패: 봇 권한 부족")
                can_change_nickname = False
            elif member.top_role >= guild.me.top_role:
                 print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}]  ⚠️ Nickname change failed for {member.name}: Cannot change nickname of user with higher or equal role.")
                 role_messages.append("닉네임 변경 실패: 대상의 역할이 봇보다 높거나 같음")
                 can_change_nickname = False

            if can_change_nickname:
                try:
                    await member.edit(nick=new_nickname, reason="자기소개 완료 후 닉네임 변경")
                    print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Nickname changed successfully for {member.name} to '{new_nickname}'")
                    role_messages.append(f"✅ 닉네임 변경 완료: {new_nickname}")
                except discord.Forbidden:
                    error_msg = "닉네임 변경 실패: 권한 부족 (API 거부)"
                    print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}]  ⚠️ Nickname change failed for {member.name}: Forbidden (likely permissions issue).")
                    role_messages.append(error_msg)
                except discord.HTTPException as e:
                     error_msg = f"닉네임 변경 실패: API 오류 ({e})"
                     print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}]  ⚠️ Nickname change failed for {member.name}: HTTPException ({e})")
                     role_messages.append(error_msg)
                except Exception as e:
                    error_msg = f"닉네임 변경 실패: 알 수 없는 오류 ({e})"
                    print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}]  ⚠️ Nickname change failed for {member.name}: Unknown error ({e})")
                    role_messages.append(error_msg)
            # --- 닉네임 변경 로직 끝 ---

        except discord.Forbidden:
             error_msg = f"⚠️ **역할 부여 실패:** 최종 단계에서 권한 부족 확인됨."
             role_messages.append(error_msg)
             print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Role assignment failed for {member.name}: {error_msg}")
        except discord.HTTPException as e:
            error_msg = f"⚠️ **역할 부여 실패:** API 오류 ({e})"
            role_messages.append(error_msg)
            print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Role assignment failed for {member.name}: {error_msg}")
        except Exception as e:
            error_msg = f"⚠️ **역할 부여 실패:** 알 수 없는 오류 ({e})"
            role_messages.append(error_msg)
            print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Role assignment failed for {member.name}: {error_msg}")
    elif not role_messages: # 부여할 역할도 없고 오류 메시지도 없다면
         info_msg = "ℹ️ 처리할 역할이 없거나 이미 모든 필수 역할을 보유하고 있습니다."
         role_messages.append(info_msg)

    # --- 최종 메시지 포맷 (임베드로 변경) ---
    avatar_url = member.display_avatar.url
    joined_at_str = "알 수 없음"
    if member.joined_at:
        # UTC 시간을 KST로 변환 (UTC+9)
        kst_joined_at = member.joined_at + timedelta(hours=9)
        joined_at_str = kst_joined_at.strftime("%Y년 %m월 %d일 %H:%M") + " (KST)"

    # 명령어 호출 시간 (KST 변환)
    kst_invoked_at = interaction.created_at + timedelta(hours=9)
    invoked_at_str = kst_invoked_at.strftime("%Y년 %m월 %d일 %H:%M") + " (KST)"

    embed = discord.Embed(
        title=f"📌 {member.display_name}님의 자기소개",
        description=f"{member.mention}님의 정보가 등록되었습니다.",
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=avatar_url)

    # 입력된 정보 필드 추가
    embed.add_field(name="👤 닉네임", value=닉네임, inline=True)
    embed.add_field(name="⚧️ 성별", value=성별, inline=True)
    embed.add_field(name="🎂 나이", value=나이, inline=True)
    embed.add_field(name="🎮 플레이 하는 게임", value=플레이_하는_게임, inline=False)
    embed.add_field(name="💬 한마디", value=자기소개, inline=False)

    # 추가 정보 필드
    embed.add_field(name="🗓️ 서버 입장일", value=joined_at_str, inline=False)
    embed.add_field(name="⏱️ 등록 시간", value=invoked_at_str, inline=False)

    # 역할 부여 및 닉네임 변경 결과 메시지 (필요 시 주석 해제)
    embed.set_footer(text=f"요청자: {interaction.user.name}")
    embed.timestamp = discord.utils.utcnow()

    # ephemeral=False로 설정하여 채널에 보이게 함 (이제 followup 사용)
    try:
        print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Preparing to send followup message for {interaction.user.name}.")
        await interaction.followup.send(embed=embed)
        print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Followup message sent for {interaction.user.name}.")
    except Exception as e:
        print(f"자기소개 메시지 전송 실패: {e}")
        # 실패 시 사용자에게 비공개 메시지로 알림
        try:
            await interaction.followup.send("자기소개 등록 메시지를 보내는 중 오류가 발생했습니다.", ephemeral=True)
        except: # 비공개 메시지조차 보낼 수 없는 경우
            pass


# --- 건의함 기능 --- #

@bot.tree.command(name="건의함input", description="건의사항을 입력받을 채널을 설정합니다. (관리자 전용)")
@app_commands.describe(channel="건의사항을 입력할 채널을 선택하세요.")
@app_commands.checks.has_permissions(administrator=True)
async def set_suggestion_input_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global suggestion_input_channel_id
    suggestion_input_channel_id = channel.id
    await interaction.response.send_message(f"✅ 건의사항 입력 채널이 {channel.mention}으로 설정되었습니다.", ephemeral=True)

@bot.tree.command(name="건의함output", description="건의사항이 출력될 채널을 설정합니다. (관리자 전용)")
@app_commands.describe(channel="건의사항이 출력될 채널을 선택하세요.")
@app_commands.checks.has_permissions(administrator=True)
async def set_suggestion_output_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    global suggestion_output_channel_id
    suggestion_output_channel_id = channel.id
    await interaction.response.send_message(f"✅ 건의사항 출력 채널이 {channel.mention}으로 설정되었습니다.", ephemeral=True)

@bot.tree.command(name="건의함mentionrole", description="건의사항 알림 시 맨션할 역할을 설정합니다. (관리자 전용)")
@app_commands.describe(role="건의사항 알림을 받을 역할을 선택하세요.")
@app_commands.checks.has_permissions(administrator=True)
async def set_suggestion_mention_role(interaction: discord.Interaction, role: discord.Role):
    """ 건의사항 알림 시 맨션할 역할을 설정합니다. """
    global suggestion_mention_role_id
    suggestion_mention_role_id = role.id
    await interaction.response.send_message(f"✅ 건의사항 알림 역할이 {role.mention}으로 설정되었습니다.", ephemeral=True)
    print(f"[{datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S KST')}] Suggestion mention role set to {role.name}({role.id}) by {interaction.user.name}")

@bot.tree.command(name="건의함", description="건의사항을 작성하여 제출합니다.")
@app_commands.describe(건의내용="전달할 건의 내용을 입력하세요.")
async def submit_suggestion(interaction: discord.Interaction, 건의내용: str):
    """ 사용자가 건의사항을 입력하면 설정된 출력 채널로 임베드 메시지를 전송합니다. """
    global suggestion_input_channel_id, suggestion_output_channel_id
    global suggestion_mention_role_id # 맨션 역할 ID 접근 추가

    # 1. 채널 설정 확인
    if not suggestion_input_channel_id or not suggestion_output_channel_id:
        await interaction.response.send_message("⚠️ 건의함 입력 또는 출력 채널이 아직 설정되지 않았습니다. 관리자에게 문의하세요.", ephemeral=True)
        return

    # 2. 입력 채널 확인
    if interaction.channel_id != suggestion_input_channel_id:
        input_channel = bot.get_channel(suggestion_input_channel_id)
        channel_mention = f"<#{suggestion_input_channel_id}>" if input_channel else f"ID: {suggestion_input_channel_id}"
        await interaction.response.send_message(f"⚠️ 이 명령어는 {channel_mention} 채널에서만 사용할 수 있습니다.", ephemeral=True)
        return

    # 3. 출력 채널 가져오기
    output_channel = bot.get_channel(suggestion_output_channel_id)
    if not output_channel:
        await interaction.response.send_message("⚠️ 설정된 건의사항 출력 채널을 찾을 수 없습니다. 관리자에게 문의하세요.", ephemeral=True)
        print(f"[ERROR] Suggestion output channel with ID {suggestion_output_channel_id} not found.")
        return
    if not isinstance(output_channel, discord.TextChannel):
         await interaction.response.send_message("⚠️ 설정된 건의사항 출력 채널이 텍스트 채널이 아닙니다. 관리자에게 문의하세요.", ephemeral=True)
         print(f"[ERROR] Suggestion output channel {output_channel.name}({suggestion_output_channel_id}) is not a TextChannel.")
         return

    # 4. 임베드 메시지 생성
    now_kst = datetime.now(pytz.timezone('Asia/Seoul'))
    kst_time_str = now_kst.strftime("%Y년 %m월 %d일 %H:%M:%S KST")

    embed = discord.Embed(
        title="📬 새로운 건의사항",
        color=discord.Color.blue(),
        timestamp=now_kst # 임베드 자체 타임스탬프 (선택적)
    )
    embed.add_field(name="👤 작성자", value=interaction.user.mention, inline=False)
    embed.add_field(name="⏰ 건의 시간", value=kst_time_str, inline=False)
    embed.add_field(name="📝 내용", value=f"> {건의내용}", inline=False) # 인용구 스타일 적용
    embed.set_footer(text=f"User ID: {interaction.user.id}")

    # 5. 출력 채널로 메시지 전송
    try:
        mention_content = None
        if suggestion_mention_role_id:
            mention_content = f"<@&{suggestion_mention_role_id}>"

        await output_channel.send(content=mention_content, embed=embed) # content 인자 추가
        await interaction.response.send_message("✅ 건의사항이 성공적으로 제출되었습니다.", ephemeral=True)
        print(f"[{kst_time_str}] Suggestion submitted by {interaction.user.name}({interaction.user.id}) in channel {interaction.channel.name}: {건의내용}")
    except discord.Forbidden:
        await interaction.response.send_message("⚠️ 건의사항을 출력 채널에 전송할 권한이 없습니다. 봇 권한을 확인해주세요.", ephemeral=True)
        print(f"[ERROR] Bot lacks permission to send messages in suggestion output channel {output_channel.name}({suggestion_output_channel_id}).")
    except discord.HTTPException as e:
        await interaction.response.send_message(f"⚠️ 건의사항 전송 중 오류가 발생했습니다: {e}", ephemeral=True)
        print(f"[ERROR] Failed to send suggestion to output channel {output_channel.name}({suggestion_output_channel_id}): {e}")
    except Exception as e:
        await interaction.response.send_message("⚠️ 건의사항 전송 중 알 수 없는 오류가 발생했습니다.", ephemeral=True)
        print(f"[ERROR] Unknown error sending suggestion: {e}")

# --- 건의함 기능 끝 --- #


# Run the bot
bot.run(os.getenv('DISCORD_TOKEN')) 