# Discord Music Bot

A Discord bot that can play music from YouTube links using discord.py and yt-dlp.

## Prerequisites

- Python 3.8 or higher
- FFmpeg installed on your system
- Discord Bot Token

## Installation

1. Clone this repository
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Install FFmpeg if you haven't already:
   - Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`

4. Create a `.env` file and add your Discord bot token:
   ```
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

## Usage

1. Run the bot:
   ```bash
   python bot.py
   ```

2. Commands:
   - `!join` - Bot joins your voice channel
   - `!play <url>` - Play a YouTube video
   - `!stop` - Stop playing and clear the queue
   - `!skip` - Skip the current song
   - `!queue` - Show the current queue

## Features

- Play music from YouTube links
- Queue system for multiple songs
- Basic music controls (play, stop, skip)
- Automatic voice channel joining
- Queue management

## Note

Make sure to replace `your_discord_bot_token_here` in the `.env` file with your actual Discord bot token. 