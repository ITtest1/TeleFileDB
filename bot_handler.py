import logging
import os
import time
import shutil
import asyncio
import queue
import threading
import requests
from pyrogram import Client
from config import TELEGRAM_BOT_TOKEN, CACHE_MAX_SIZE_GB, CACHE_MAX_AGE_MINUTES
from pyrogram_clients import client_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
CACHE_DIR = "./cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

class PyrogramRunner:
    def __init__(self):
        self.loop = None
        self.thread = None
        self.request_queue = None

    async def _worker(self):
        logger.info("Pyrogram worker for large files started.")
        if not client_manager.client or not client_manager.client.is_connected:
            logger.info("Starting shared Pyrogram client for worker.")
            await client_manager.start()

        while True:
            file_id, result_queue, cache_file_path = await self.request_queue.get()
            try:
                with open(cache_file_path, 'wb') as f:
                    async for chunk in client_manager.client.stream_media(file_id):
                        if chunk:
                            f.write(chunk)
                            result_queue.put(chunk)
            except Exception as e:
                logger.error(f"Error processing file_id {file_id} in Pyrogram worker: {e}", exc_info=True)
                result_queue.put(e)
            finally:
                result_queue.put(None)

    def _start_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.request_queue = asyncio.Queue()
        self.loop.run_until_complete(self._worker())

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._start_loop, daemon=True)
            self.thread.start()
            logger.info("PyrogramRunner thread started.")

    def get_stream_queue(self, file_id, cache_file_path):
        if self.loop is None or not self.loop.is_running():
            raise RuntimeError("PyrogramRunner is not running.")
        
        result_queue = queue.Queue()
        asyncio.run_coroutine_threadsafe(self.request_queue.put((file_id, result_queue, cache_file_path)), self.loop)
        return result_queue

pyrogram_runner = PyrogramRunner()

def stream_and_cache_telegram_file(file_id, cancellable=True):
    cache_file_path = os.path.join(CACHE_DIR, file_id)

    if os.path.exists(cache_file_path) and (time.time() - os.path.getmtime(cache_file_path) < CACHE_MAX_AGE_MINUTES * 60):
        logging.info(f"Streaming from valid cache file: {cache_file_path}")
        with open(cache_file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk: break
                yield chunk
        return

    logging.info(f"Attempting to stream via Bot API: {file_id}")
    url = f"{TELEGRAM_API_URL}/getFile?file_id={file_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        file_path_from_telegram = response.json()['result']['file_path']
        telegram_download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path_from_telegram}"
        
        logging.info(f"Streaming from Bot API direct URL: {telegram_download_url}")
        with requests.get(telegram_download_url, stream=True) as file_content_response, open(cache_file_path, 'wb') as f:
            file_content_response.raise_for_status()
            for chunk in file_content_response.iter_content(chunk_size=8192):
                f.write(chunk)
                yield chunk
        return

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400 and "file is too big" in e.response.text:
            logging.warning(f"File {file_id} is too large for Bot API, falling back to Pyrogram client.")
            # Fallback to PyrogramRunner for large files
            result_queue = pyrogram_runner.get_stream_queue(file_id, cache_file_path)
            while True:
                chunk = result_queue.get()
                if chunk is None: break
                if isinstance(chunk, Exception): raise chunk
                yield chunk
            return
        else:
            logging.error(f"HTTPError getting file_path from Telegram API: {e}. Full response: {e.response.text}")
            if os.path.exists(cache_file_path): os.remove(cache_file_path)
            return

    except Exception as e:
        logging.error(f"An unexpected error occurred during streaming: {e}")
        if os.path.exists(cache_file_path): os.remove(cache_file_path)
        return

def clean_cache():
    # ... implementation ...
    pass

def get_current_cache_size_bytes():
    # ... implementation ...
    pass

def clear_cache_manual():
    logging.info("Manually clearing cache...")
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
        os.makedirs(CACHE_DIR, exist_ok=True)
        logging.info("Cache directory recreated.")
    else:
        logging.info("Cache directory does not exist.")
    logging.info("Manual cache clear finished.")
