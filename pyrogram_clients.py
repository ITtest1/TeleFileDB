
import asyncio # 導入 asyncio 模組，用於異步操作
import queue # 導入 queue 模組，用於隊列操作
import threading # 導入 threading 模組，用於多線程
import logging # 導入 logging 模組，用於日誌記錄
import os # 導入 os 模組，用於操作文件系統
from pyrogram import Client
from pyrogram.errors import PeerIdInvalid
from pyrogram.handlers import RawUpdateHandler
from config import API_ID, API_HASH, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID # 從 config 導入配置參數
from database import add_file

logging.basicConfig(level=logging.INFO) # 配置日誌級別為 INFO
logger = logging.getLogger(__name__) # 獲取當前模塊的日誌記錄器



class PyrogramClientManager: # Pyrogram 客戶端管理器類
    def __init__(self, telegram_chat_id): # 構造函數，接受 telegram_chat_id
        self.client = None # Initialize client to None
        self.telegram_chat_id = telegram_chat_id # 存儲 telegram_chat_id

    async def start(self):
        if self.client is None:
            self.client = Client(
                "pyrogram_client",
                api_id=API_ID,
                api_hash=API_HASH,
                bot_token=TELEGRAM_BOT_TOKEN
            )
            # WAL mode handler
            self.wal_mode_set = False
            async def wal_handler(client, update, users, chats):
                if not self.wal_mode_set:
                    try:
                        client.storage.conn.execute("PRAGMA journal_mode=WAL;")
                        client.storage.conn.commit()
                        logger.info("WAL mode enabled for Pyrogram client session.")
                        self.wal_mode_set = True
                    except Exception as e:
                        logger.error(f"Error setting WAL mode in main client: {e}")
                return False
            self.client.add_handler(RawUpdateHandler(wal_handler), group=-1) # Add as the first handler

        await self.client.start()
        me = await self.client.get_me()
        logger.info(f"Pyrogram client started successfully. Bot: @{me.username} (ID: {me.id})")

        try:
            target_chat_id_int = int(self.telegram_chat_id) if isinstance(self.telegram_chat_id, str) and self.telegram_chat_id.startswith('-100') else self.telegram_chat_id
            chat_info = await self.client.get_chat(target_chat_id_int)
            logger.info(f"Successfully retrieved chat info for target chat: {chat_info.title} (ID: {chat_info.id})")
        except Exception as e:
            logger.error(f"Error getting chat info for TELEGRAM_CHAT_ID {self.telegram_chat_id}: {e}. Please ensure the bot is added to this chat/channel and has necessary permissions.")

    async def stop(self):
        if self.client:
            await self.client.stop()
            logger.info("Pyrogram client stopped.")

async def perform_pyrogram_upload(client, file_path, file_name, chat_id, mime_type, size, thumbnail_path=None):
    try:
        chat_info = await client.get_chat(chat_id)
        chat_title = getattr(chat_info, 'title', str(chat_id))
        logger.info(f"Attempting to upload file {file_name} from {file_path} to chat: {chat_title} (ID: {chat_id})")

        if not os.path.exists(file_path):
            logger.error(f"Local file not found for upload: {file_path}")
            return None, None, None, None, None, None

        thumbnail_file_id = None
        if thumbnail_path and os.path.exists(thumbnail_path):
            logger.info(f"Uploading thumbnail separately: {thumbnail_path}")
            try:
                thumb_message = await client.send_photo(chat_id=chat_id, photo=thumbnail_path)
                if thumb_message and thumb_message.photo:
                    thumbnail_file_id = thumb_message.photo.file_id
                    logger.info(f"Thumbnail uploaded separately, file_id: {thumbnail_file_id}")
                else:
                    logger.warning("Thumbnail upload via send_photo did not return a photo object.")
            except Exception as e:
                logger.error(f"Error uploading thumbnail separately: {e}")
                pass # Continuing without a thumbnail

        message = None
        if mime_type.startswith("video/"):
            logger.info(f"Uploading {file_name} as a video.")
            message = await client.send_video(chat_id=chat_id, video=file_path, file_name=file_name)
        else:
            logger.info(f"Uploading {file_name} as a document.")
            message = await client.send_document(chat_id=chat_id, document=file_path, file_name=file_name)

        if message:
            message_id = message.id
            file_id = None
            uploaded_file_name = file_name
            size = None
            uploaded_mime_type = mime_type

            if message.video:
                file_id = message.video.file_id
                uploaded_file_name = message.video.file_name or file_name
                size = message.video.file_size
                uploaded_mime_type = message.video.mime_type
            elif message.document:
                file_id = message.document.file_id
                uploaded_file_name = message.document.file_name or file_name
                size = message.document.file_size
                uploaded_mime_type = message.document.mime_type
            elif message.photo:
                file_id = message.photo.file_id
                size = message.photo.file_size
                uploaded_mime_type = "image/jpeg"
            else:
                return None, "Failed to get file details from the sent message.", None, None, None, None
            
            return file_id, uploaded_file_name, uploaded_mime_type, size, thumbnail_file_id, message_id
        else:
            return None, "Failed to send file to Telegram.", None, None, None, None

    except PeerIdInvalid as e:
        logger.error(f"PEER_ID_INVALID error for chat {chat_id}: {e}. This usually means the bot is not in the chat/channel or does not have permissions. Please add the bot to the chat/channel and ensure it has necessary permissions (e.g., Post Messages for channels).")
        return None, f"Telegram says: [400 PEER_ID_INVALID] - The peer id being used is invalid or not known yet. Make sure you meet the peer before interacting with it ", None, None, None, None
    except Exception as e:
        logger.error(f"Error during Pyrogram upload of {file_name} to chat {chat_id}: {e}")
        return None, str(e), None, None, None, None

# 全局實例
client_manager = PyrogramClientManager(telegram_chat_id=TELEGRAM_CHAT_ID) # 創建 PyrogramClientManager 的全局實例，並傳遞 TELEGRAM_CHAT_ID
