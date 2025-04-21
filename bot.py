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