import asyncio
import random
import os
import shutil
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile, BotCommand
from aiogram.filters import Command
import yt_dlp
from yandex_music import Client

from db import init_db, add_user, log_download
from config import BOT_TOKEN, YANDEX_TOKEN, PROXIES

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

MAX_PARALLEL_PROXY_DOWNLOADS = 4
MAX_PLAYLIST_ITEMS = 20
MAX_TELEGRAM_FILE_SIZE_MB = 50
DOWNLOADS_DIR = "video"

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".ogg", ".wav"}

URL_REGEX = re.compile(r"https?://[^\s]+")

async def human_delay(message: Message, action: str = "typing", min_sec: float = 1.0, max_sec: float = 2.5):
    await bot.send_chat_action(chat_id=message.chat.id, action=action)
    await asyncio.sleep(random.uniform(min_sec, max_sec))

def sort_files(files: list[str]) -> list[str]:
    def weight(path: str) -> int:
        ext = os.path.splitext(path)[1].lower()
        if ext in VIDEO_EXTENSIONS: return 0
        if ext in AUDIO_EXTENSIONS: return 1
        return 2
    return sorted(files, key=weight)

async def send_file(chat_id: int, file_path: str, caption: str):
    ext = os.path.splitext(file_path)[1].lower()
    media = FSInputFile(file_path)

    if ext in VIDEO_EXTENSIONS:
        await bot.send_video(chat_id=chat_id, video=media, caption=caption, supports_streaming=True)
    elif ext in AUDIO_EXTENSIONS:
        await bot.send_audio(chat_id=chat_id, audio=media, caption=caption)
    else:
        await bot.send_document(chat_id=chat_id, document=media, caption=caption)

def download_yandex(url: str, output_dir: str, token: str) -> list[str]:
    print("Скачиваю из Яндекс Музыки...")
    client = Client(token).init()
    os.makedirs(output_dir, exist_ok=True)
    downloaded = []

    def save(track, prefix=""):
        if len(downloaded) >= MAX_PLAYLIST_ITEMS: return False
        artists = ", ".join(a.name for a in track.artists) if track.artists else "Unknown"
        name = re.sub(r'[\\/*?:"<>|]', "", f"{artists} - {track.title}")
        path = os.path.join(output_dir, f"{prefix}{name}.mp3")
        track.download(path)
        downloaded.append(path)
        return True

    if "track/" in url:
        t_id = re.search(r'track/(\d+)', url).group(1)
        a_id = re.search(r'album/(\d+)', url).group(1)
        save(client.tracks(f"{t_id}:{a_id}")[0])
    elif "album/" in url:
        a_id = re.search(r'album/(\d+)', url).group(1)
        album = client.albums_with_tracks(a_id)
        for vol in album.volumes:
            for i, tr in enumerate(vol):
                save(tr, prefix=f"{i+1:02d}_")
    elif "playlists/" in url:
        u_id = re.search(r'users/([^/]+)', url).group(1)
        p_id = re.search(r'playlists/(\d+)', url).group(1)
        plist = client.users_playlists(int(p_id), u_id)
        for i, tr_short in enumerate(plist.tracks):
            if not save(tr_short.fetch_track(), prefix=f"{i+1:02d}_"): break
    return downloaded

def download_other(url: str, output_dir: str) -> list[str]:
    def worker(proxy, path):
        os.makedirs(path, exist_ok=True)
        opts = {
            "format": f"bv*+ba/b[filesize<{MAX_TELEGRAM_FILE_SIZE_MB}M]/best",
            "outtmpl": os.path.join(path, "%(title).80s.%(ext)s"),
            "quiet": True,
            "noplaylist": False,
            "playlistend": MAX_PLAYLIST_ITEMS,
            "ignoreerrors": True,
            "merge_output_format": "mp4",
            "proxy": proxy if proxy else ""
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return [os.path.join(path, f) for f in os.listdir(path) if not f.endswith(('.part', '.ytdl'))]

    proxies = random.sample(PROXIES, min(len(PROXIES), MAX_PARALLEL_PROXY_DOWNLOADS - 1)) if PROXIES else []
    targets = proxies + [None]
    
    with ThreadPoolExecutor(max_workers=len(targets)) as ex:
        futures = [ex.submit(worker, p, os.path.join(output_dir, f"w{i}")) for i, p in enumerate(targets)]
        for f in as_completed(futures):
            try:
                res = f.result()
                if res:
                    final = []
                    for s in res:
                        d = os.path.join(output_dir, os.path.basename(s))
                        os.replace(s, d)
                        final.append(d)
                    return sorted(final)
            except: continue
    raise Exception("Не удалось скачать файл.")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await add_user(message.from_user.id, message.from_user.username)
    await human_delay(message)
    await message.answer("Пришли ссылку на видео или музыку, и я скачаю её.")

@dp.message(F.text.regexp(URL_REGEX))
async def handle_link(message: Message):
    url = re.search(URL_REGEX, message.text).group(0)
    await log_download(message.from_user.id, url)
    await human_delay(message, min_sec=0.5, max_sec=1.5)
    
    msg = await message.answer("Начинаю скачивание...")
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    folder = os.path.join(DOWNLOADS_DIR, f"task_{random.randint(100, 999)}")
    
    try:
        asyncio.create_task(human_delay(message, action="upload_video"))
        
        if "music.yandex" in url:
            if not YANDEX_TOKEN:
                await msg.edit_text("в настройках нет токена Яндекса.")
                return
            files = await asyncio.to_thread(download_yandex, url, folder, YANDEX_TOKEN)
        else:
            files = await asyncio.to_thread(download_other, url, folder)
            
        files = sort_files(files)
        
        if files:
            await msg.edit_text("Отправляю файл...")
            for i, f in enumerate(files, 1):
                cap = f"Часть {i}" if len(files) > 1 else ""
                await send_file(message.chat.id, f, cap)
            await msg.delete()
        else:
            await msg.edit_text("Не удалось найти файл")

    except Exception as e:
        await msg.edit_text(f"Произошла ошибка:\n{str(e)}")
        
    finally:
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)

async def main():
    await init_db()
    await bot.set_my_commands([BotCommand(command="start", description="Старт")])
    print("Бот запущен.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())