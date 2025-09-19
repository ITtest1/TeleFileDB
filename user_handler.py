from pyrogram import Client, filters # 從 pyrogram 導入 Client 和 filters
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneNumberInvalid, PeerIdInvalid # 從 pyrogram.errors 導入錯誤類型
from config import API_ID, API_HASH, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT # 從 config 導入配置參數
import os # 導入 os 模組，用於操作文件系統
import asyncio # 導入 asyncio 模組，用於異步操作
import logging # 導入 logging 模組，用於日誌記錄
import queue # 導入 queue 模組，用於隊列操作
import threading # 導入 threading 模組，用於多線程
from PIL import Image # 導入 Pillow 庫的 Image 模組
import subprocess # 導入 subprocess 模組，用於運行外部命令（如 ffmpeg）

logging.basicConfig(level=logging.INFO) # 配置日誌級別為 INFO

# Bot 賬戶的會話名稱
BOT_SESSION_NAME = "bot_account_session"

async def get_bot_client(): # 獲取 Bot 客戶端的異步函數
    """
    初始化並返回一個用於 Bot 賬戶的 Pyrogram 客戶端。
    """
    if not API_ID or not API_HASH or not TELEGRAM_BOT_TOKEN: # 檢查配置參數是否設置
        logging.error("Configuration error: API_ID, API_HASH, and TELEGRAM_BOT_TOKEN must be configured for bot client.") # 記錄配置錯誤
        raise ValueError("API_ID, API_HASH, and TELEGRAM_BOT_TOKEN must be configured for bot client.") # 拋出值錯誤

    app = Client( # 創建 Pyrogram 客戶端實例
        BOT_SESSION_NAME, # 會話名稱
        api_id=API_ID, # API ID
        api_hash=API_HASH, # API Hash
        bot_token=TELEGRAM_BOT_TOKEN # Bot Token
    )
    try:
        await app.start() # 啟動客戶端
        me = await app.get_me() # 獲取 Bot 自身信息
        logging.info(f"Pyrogram bot client started successfully. Bot: @{me.username} (ID: {me.id})") # 記錄客戶端啟動成功和 Bot 信息
        return app # 返回客戶端實例
    except Exception as e: # 捕獲啟動錯誤
        logging.error(f"Error starting Pyrogram bot client: {e}") # 記錄啟動錯誤
        raise # 重新拋出異常

async def send_file_with_pyrogram(file_path, file_name, mime_type, file_size, thumbnail_path=None): # 使用 Pyrogram 發送文件的異步函數
    """
    使用 Pyrogram 通過 Bot 賬戶將文件上傳到 Telegram。
    接受 file_path 和可選的 thumbnail_path。
    """
    if not API_ID or not API_HASH or not TELEGRAM_BOT_TOKEN: # 檢查配置參數是否設置
        return None, "API_ID, API_HASH, and TELEGRAM_BOT_TOKEN are not configured for Pyrogram bot upload.", None, None, None, None # 返回錯誤信息

    thumbnail_file_id = None # 縮略圖文件 ID

    app = None # 初始化應用
    try:
        app = await get_bot_client() # 獲取 Bot 客戶端
        
        target_chat_id = TELEGRAM_CHAT_ID # 目標聊天 ID
        try:
            # 嘗試將 chat_id 轉換為整數（如果它是數字字符串）
            if isinstance(target_chat_id, str) and target_chat_id.startswith('-100'): # 如果是頻道 ID
                target_chat_id = int(target_chat_id) # 轉換為整數
            logging.info(f"Attempting to get chat info for chat ID: {target_chat_id} (Type: {type(target_chat_id)})") # 記錄獲取聊天信息
            chat_info = await app.get_chat(target_chat_id) # 獲取聊天信息
            logging.info(f"Successfully retrieved chat info for {target_chat_id}: {chat_info.title}") # 記錄成功獲取聊天信息
        except PeerIdInvalid as e: # 捕獲 PeerIdInvalid 錯誤
            logging.error(f"PEER_ID_INVALID error for chat {target_chat_id}: {e}. This usually means the bot is not in the chat/channel or does not have permissions. Please add the bot to the chat/channel and ensure it has necessary permissions (e.g., Post Messages for channels).") # 記錄錯誤信息
            return None, f"Telegram says: [400 PEER_ID_INVALID] - The peer id being used is invalid or not known yet. Make sure you meet the peer before interacting with it ", None, None, None, None # 返回錯誤信息
        except Exception as e: # 捕獲其他異常
            logging.error(f"Failed to get chat info for {target_chat_id}: {e}") # 記錄錯誤信息
            return None, f"Failed to get chat info for {target_chat_id}: {e}", None, None, None, None # 返回錯誤信息

        # 如果提供了縮略圖且存在，則上傳縮略圖
        if thumbnail_path and os.path.exists(thumbnail_path): # 如果縮略圖路徑存在且文件存在
            try:
                thumb_message = await app.send_photo(chat_id=target_chat_id, photo=thumbnail_path) # 發送縮略圖
                if thumb_message and thumb_message.photo: # 如果消息存在且包含照片
                    thumbnail_file_id = thumb_message.photo.file_id # 獲取縮略圖文件 ID
                    logging.info(f"Thumbnail uploaded, file_id: {thumbnail_file_id}") # 記錄縮略圖上傳成功
            except Exception as e: # 捕獲上傳錯誤
                logging.error(f"Error uploading thumbnail: {e}") # 記錄錯誤信息
                thumbnail_file_id = None # 縮略圖文件 ID 設置為 None

        # 根據 MIME 類型確定適當的 Pyrogram 方法
        message = None # 初始化消息

        if mime_type.startswith("image/"): # 如果是圖片類型
            # 對於大於 1MB 的圖片，作為文檔發送
            if file_size and file_size > 1 * 1024 * 1024: # 1MB
                logging.info(f"Image {file_name} is larger than 1MB, sending as document.") # 記錄圖片太大，作為文檔發送
                message = await app.send_document(chat_id=target_chat_id, document=file_path, file_name=file_name, thumb=thumbnail_path) # 發送文檔
            else:
                try:
                    message = await app.send_photo(chat_id=target_chat_id, photo=file_path) # 發送照片
                except (PeerIdInvalid, Exception) as e: # 捕獲特定的 Telegram 錯誤
                    logging.warning(f"Failed to send photo {file_name} directly: {e}. Attempting to send as document instead.") # 警告發送失敗，嘗試作為文檔發送
                    message = await app.send_document(chat_id=target_chat_id, document=file_path, file_name=file_name, thumb=thumbnail_path) # 發送文檔
        elif mime_type.startswith("video/"): # 如果是視頻類型
            message = await app.send_video(chat_id=target_chat_id, video=file_path, file_name=file_name, thumb=thumbnail_path) # 發送視頻
        else:
            message = await app.send_document(chat_id=target_chat_id, document=file_path, file_name=file_name, thumb=thumbnail_path) # 發送文檔
        
        # 從發送的消息中提取文件 ID、文件名、MIME 類型和大小
        if message: # 如果消息存在
            message_id = message.id # 消息 ID
            if message.photo: # 如果是照片
                file_id = message.photo.file_id # 文件 ID
                uploaded_file_name = file_name # 使用原始文件名
                size = message.photo.file_size # 文件大小
                uploaded_mime_type = "image/jpeg" # Telegram 將照片轉換為 JPEG
            elif message.video: # 如果是視頻
                file_id = message.video.file_id # 文件 ID
                uploaded_file_name = message.video.file_name or file_name # 文件名
                size = message.video.file_size # 文件大小
                uploaded_mime_type = message.video.mime_type # MIME 類型
            elif message.document: # 如果是文檔
                file_id = message.document.file_id # 文件 ID
                uploaded_file_name = message.document.file_name or file_name # 文件名
                size = message.document.file_size # 文件大小
                uploaded_mime_type = message.document.mime_type # MIME 類型
            else:
                return None, "Failed to get file details from the sent message.", None, None, None, None # 返回錯誤信息
            
            return file_id, uploaded_file_name, uploaded_mime_type, size, thumbnail_file_id, message_id # 返回文件信息
        else:
            return None, "Failed to send file to Telegram.", None, None, None, None # 返回錯誤信息

    except Exception as e: # 捕獲異常
        logging.error(f"Error during Pyrogram upload: {e}") # 記錄 Pyrogram 上傳錯誤
        return None, str(e), None, None, None, None # 返回錯誤信息
    finally:
        if app and app.is_connected: # 如果應用存在且已連接
            await app.stop() # 停止應用
            logging.info("Pyrogram bot client stopped.") # 記錄客戶端已停止

async def upload_thumbnail_with_pyrogram(thumbnail_path): # 使用 Pyrogram 上傳縮略圖的異步函數
    """
    使用 Pyrogram 通過 Bot 賬戶將縮略圖文件上傳到 Telegram 並返回其 file_id。
    """
    if not API_ID or not API_HASH or not TELEGRAM_BOT_TOKEN: # 檢查配置參數是否設置
        logging.error("Configuration error: API_ID, API_HASH, and TELEGRAM_BOT_TOKEN must be configured for thumbnail upload.") # 記錄配置錯誤
        return None # 返回 None

    if not thumbnail_path or not os.path.exists(thumbnail_path): # 如果縮略圖路徑無效或文件不存在
        logging.warning(f"Thumbnail path is invalid or file does not exist: {thumbnail_path}") # 記錄警告信息
        return None # 返回 None

    app = None # 初始化應用
    try:
        app = await get_bot_client() # 獲取 Bot 客戶端
        target_chat_id = TELEGRAM_CHAT_ID # 目標聊天 ID
        try:
            if isinstance(target_chat_id, str) and target_chat_id.startswith('-100'): # 如果是頻道 ID
                target_chat_id = int(target_chat_id) # 轉換為整數
            await app.get_chat(target_chat_id) # 確保聊天可訪問
        except Exception as e: # 捕獲異常
            logging.error(f"Failed to get chat info for {target_chat_id} during thumbnail upload: {e}") # 記錄錯誤信息
            return None # 返回 None

        thumb_message = await app.send_photo(chat_id=target_chat_id, photo=thumbnail_path) # 發送照片
        if thumb_message and thumb_message.photo: # 如果消息存在且包含照片
            logging.info(f"Thumbnail uploaded successfully, file_id: {thumb_message.photo.file_id}") # 記錄縮略圖上傳成功
            return thumb_message.photo.file_id # 返回文件 ID
        else:
            logging.error("Failed to get file_id from uploaded thumbnail message.") # 記錄無法從上傳的縮略圖消息中獲取文件 ID
            return None # 返回 None
    except Exception as e: # 捕獲異常
        logging.error(f"Error uploading thumbnail with Pyrogram: {e}") # 記錄 Pyrogram 上傳縮略圖錯誤
        return None # 返回 None
    finally:
        if app and app.is_connected: # 如果應用存在且已連接
            await app.stop() # 停止應用
            logging.info("Pyrogram bot client stopped.") # 記錄客戶端已停止

async def generate_thumbnail(file_path, mime_type): # 生成縮略圖的異步函數
    logging.info(f"Generating thumbnail for {file_path} with dimensions: {THUMBNAIL_WIDTH}x{THUMBNAIL_HEIGHT}") # 記錄生成縮略圖信息
    thumbnail_output_path = None # 縮略圖輸出路徑
    try:
        if mime_type.startswith("image/"): # 如果是圖片類型
            img = Image.open(file_path) # 打開圖片文件
            if img.mode == 'RGBA': # 如果圖片模式是 RGBA
                img = img.convert('RGB') # 轉換為 RGB 模式
            img.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT)) # 生成縮略圖
            thumbnail_output_path = f"{file_path}.tHuMb20821132.jpg" # 構建縮略圖輸出路徑
            try:
                img.save(thumbnail_output_path, "JPEG") # 保存縮略圖為 JPEG 格式
                logging.info(f"Image thumbnail saved to: {thumbnail_output_path}") # 記錄縮略圖保存成功
            except Exception as save_e:
                logging.error(f"Error saving image thumbnail {thumbnail_output_path}: {save_e}") # 記錄保存縮略圖錯誤
                thumbnail_output_path = None
        elif mime_type.startswith("video/"): # 如果是視頻類型
            thumbnail_output_path = f"{file_path}.tHuMb20821132.jpg" # 構建縮略圖輸出路徑
            # 使用 ffmpeg 從視頻中提取一幀
            command = [ # ffmpeg 命令
                "ffmpeg",
                "-i", file_path,
                "-ss", "00:00:01", # 在 1 秒處截圖
                "-vframes", "1",
                "-q:v", "2", # 質量（2 非常高，1-31，越低越好）
                "-y", # 覆蓋輸出文件
                thumbnail_output_path
            ]
            process = await asyncio.create_subprocess_exec( # 創建子進程
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate() # 獲取標準輸出和標準錯誤
            if process.returncode != 0: # 如果返回碼不為 0
                logging.error(f"ffmpeg thumbnail generation failed: {stderr.decode()}") # 記錄錯誤信息
                thumbnail_output_path = None # 縮略圖輸出路徑設置為 None
            else:
                logging.info(f"Video thumbnail saved to: {thumbnail_output_path}") # 記錄縮略圖保存成功
    except Exception as e: # 捕獲異常
        logging.error(f"Error generating thumbnail for {file_path}: {e}") # 記錄生成縮略圖錯誤
        thumbnail_output_path = None # 縮略圖輸出路徑設置為 None
    return thumbnail_output_path # 返回縮略圖輸出路徑

async def delete_telegram_message(chat_id, message_id): # 刪除 Telegram 消息的異步函數
    """
    使用 Bot 賬戶從 Telegram 刪除消息。
    """
    if not API_ID or not API_HASH or not TELEGRAM_BOT_TOKEN: # 檢查配置參數是否設置
        logging.error("Configuration error: API_ID, API_HASH, and TELEGRAM_BOT_TOKEN must be configured for bot client to delete messages.") # 記錄配置錯誤
        return False # 返回 False

    app = None # 初始化應用
    try:
        app = await get_bot_client() # 獲取 Bot 客戶端
        logging.info(f"Attempting to delete message {message_id} from chat {chat_id}") # 記錄嘗試刪除消息信息
        await app.delete_messages(chat_id, message_id) # 刪除消息
        logging.info(f"Message {message_id} deleted successfully from chat {chat_id}.") # 記錄消息刪除成功
        return True # 返回 True
    except Exception as e: # 捕獲異常
        logging.error(f"Error deleting message {message_id} from chat {chat_id}: {e}") # 記錄刪除消息錯誤
        return False # 返回 False
    finally:
        if app and app.is_connected: # 如果應用存在且已連接
            await app.stop() # 停止應用
            logging.info("Pyrogram bot client stopped.") # 記錄客戶端已停止

async def scan_channel_history(chat_id, db_add_file_func): # 掃描頻道歷史記錄的異步函數
    """
    掃描給定 chat_id 的歷史記錄並將文件信息添加到數據庫。
    """
    if not API_ID or not API_HASH or not TELEGRAM_BOT_TOKEN: # 檢查配置參數是否設置
        logging.error("Configuration error: API_ID, API_HASH, and TELEGRAM_BOT_TOKEN are not configured for scanning.") # 記錄配置錯誤
        return # 返回

    app = None # 初始化應用
    try:
        app = await get_bot_client() # 獲取 Bot 客戶端
        logging.info(f"Starting scan for chat_id: {chat_id}") # 記錄開始掃描信息
        
        target_chat_id = chat_id # 目標聊天 ID
        try:
            # 嘗試將 chat_id 轉換為整數（如果它是數字字符串）
            if isinstance(target_chat_id, str) and target_chat_id.startswith('-100'): # 如果是頻道 ID
                target_chat_id = int(target_chat_id) # 轉換為整數
            logging.info(f"Attempting to get chat info for chat ID: {target_chat_id} (Type: {type(target_chat_id)})") # 記錄獲取聊天信息
            chat_info = await app.get_chat(target_chat_id) # 獲取聊天信息
            logging.info(f"Successfully retrieved chat info for {target_chat_id}: {chat_info.title}") # 記錄成功獲取聊天信息
        except PeerIdInvalid as e: # 捕獲 PeerIdInvalid 錯誤
            logging.error(f"PEER_ID_INVALID error for chat {target_chat_id}: {e}. This usually means the bot is not in the chat/channel or does not have permissions. Please add the bot to the chat/channel and ensure it has necessary permissions (e.g., Post Messages for channels).") # 記錄錯誤信息
            return # 返回
        except Exception as e: # 捕獲其他異常
            logging.error(f"Failed to get chat info for {target_chat_id} before scanning: {e}") # 記錄錯誤信息
            return # 返回

        async for message in app.get_chat_history(target_chat_id): # 遍歷聊天歷史記錄
            if message.document: # 如果是文檔
                file_id = message.document.file_id # 文件 ID
                file_name = message.document.file_name or "Unknown File" # 文件名
                folder = "scanned_files" # 默認文件夾
                db_add_file_func(file_name, file_id, folder) # 添加文件到數據庫
                logging.info(f"Scanned file: {file_name} (ID: {file_id})") # 記錄掃描文件信息
            elif message.photo: # 如果是照片
                # 對於照片，我們可以使用最大尺寸的文件 ID
                file_id = message.photo.file_id # 文件 ID
                file_name = f"photo_{message.photo.file_id}.jpg" # 文件名
                folder = "scanned_photos" # 文件夾
                db_add_file_func(file_name, file_id, folder) # 添加文件到數據庫
                logging.info(f"Scanned photo: {file_name} (ID: {file_id})") # 記錄掃描照片信息
            # 如果需要，添加更多媒體類型（例如，視頻，音頻）

    except Exception as e: # 捕獲異常
        logging.error(f"Error during channel history scan: {e}") # 記錄頻道歷史掃描錯誤
    finally:
        if app and app.is_connected: # 如果應用存在且已連接
            await app.stop() # 停止應用
            logging.info("Pyrogram bot client stopped.") # 記錄客戶端已停止

async def get_file_info(message_id): # 獲取文件信息的異步函數
    app = await get_bot_client() # 獲取 Bot 客戶端
    try:
        # 獲取消息
        message = await app.get_messages(TELEGRAM_CHAT_ID, int(message_id)) # 獲取消息
        if not message: # 如果消息不存在
            return None, None # 返回 None

        # 提取文件信息
        file_id = None # 文件 ID
        file_name = None # 文件名
        file_size = None # 文件大小
        if message.document: # 如果是文檔
            file_id = message.document.file_id # 文件 ID
            file_name = message.document.file_name # 文件名
            file_size = message.document.file_size # 文件大小
        elif message.video: # 如果是視頻
            file_id = message.video.file_id # 文件 ID
            file_name = message.video.file_name # 文件名
            file_size = message.video.file_size # 文件大小
        elif message.photo: # 如果是照片
            file_id = message.photo.file_id # 文件 ID
            file_name = f"photo_{message.photo.file_id}.jpg" # 文件名
            file_size = message.photo.file_size # 文件大小
        
        if file_id: # 如果文件 ID 存在
            return file_name, file_size # 返回文件名和文件大小
        else:
            return None, None # 返回 None
    finally:
        if app and app.is_connected: # 如果應用存在且已連接
            await app.stop() # 停止應用

def stream_file(message_id): # 流式傳輸文件的函數
    """使用工作線程處理異步操作，從 Telegram 流式傳輸文件。"""
    q = queue.Queue() # 創建隊列
    stop_event = threading.Event() # 創建停止事件

    def worker(): # 工作線程函數
        async def stream_async(): # 異步流式傳輸函數
            app = None # 初始化應用
            try:
                app = await get_bot_client() # 獲取 Bot 客戶端
                async for chunk in app.iter_download(message_id): # 迭代下載塊
                    if stop_event.is_set(): # 如果停止事件已設置
                        logging.info(f"Streaming stopped for file_id {message_id} by client.") # 記錄流式傳輸停止信息
                        break # 跳出循環
                    q.put(chunk) # 將塊放入隊列
            except Exception as e: # 捕獲異常
                logging.error(f"Error in stream_file worker thread: {e}") # 記錄工作線程錯誤
                q.put(e) # 將錯誤放入隊列
            finally:
                if app and app.is_connected: # 如果應用存在且已連接
                    await app.stop() # 停止應用
                q.put(None)  # 發送信號表示完成

        # 每個線程都需要自己的事件循環。
        loop = asyncio.new_event_loop() # 創建新的事件循環
        asyncio.set_event_loop(loop) # 設置當前線程的事件循環
        loop.run_until_complete(stream_async()) # 運行異步任務直到完成
        loop.close() # 關閉事件循環

    thread = threading.Thread(target=worker) # 創建線程
    thread.start() # 啟動線程

    try:
        while True: # 無限循環
            chunk = q.get() # 從隊列中獲取塊
            if chunk is None: # 如果塊為 None
                break # 跳出循環
            if isinstance(chunk, Exception): # 如果塊是異常
                raise chunk # 拋出異常
            yield chunk # 返回塊
    except GeneratorExit: # 捕獲生成器退出異常
        logging.info(f"Client disconnected, stopping stream for file_id {message_id}.") # 記錄客戶端斷開連接
        stop_event.set() # 設置停止事件
    finally:
        thread.join() # 等待線程結束
