import asyncio
import os
import logging
import mimetypes
import re
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
from datetime import datetime

# Import necessary components from the Flask app
from app import create_app
from database import add_file, get_folder_id_by_path, create_folder

# --- Setup ---
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask App Context Setup ---
# We need to create a Flask app context to interact with the database
flask_app = create_app()

# --- Environment Variables & Pyrogram Client ---
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MONITORED_CHAT_IDS = [int(chat_id.strip()) for chat_id in os.getenv("MONITORED_CHAT_ID", "").split(',') if chat_id.strip()]

client = Client(
    "telegram_listener_bot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=TELEGRAM_BOT_TOKEN
)

# --- New Database Function (Adapter) ---
def add_file_with_folder_creation(filename, file_id, folder, size=None, mime_type=None, thumbnail_file_id=None, message_link=None):
    """Ensures parent folders exist before adding the file, using the new database functions."""
    try:
        with flask_app.app_context():
            path_parts = folder.split('/')
            current_path = ""
            for i, part in enumerate(path_parts):
                if i == 0:
                    current_path = part
                else:
                    current_path = f"{current_path}/{part}"
                
                if get_folder_id_by_path(current_path) is None:
                    logger.info(f"Creating folder marker for: {current_path}")
                    create_folder(current_path)

            # Now that folders are created, add the file
            add_file(filename, file_id, folder, size, mime_type, thumbnail_file_id, message_link)
            logger.info(f"Successfully added file to DB: {filename} in folder {folder}")
        return True
    except Exception as e:
        logger.error(f"Database error in add_file_with_folder_creation: {e}")
        return False

# --- Custom Argument Parsing (from old script) ---
def parse_custom_args(command_text: str):
    args = {
        'batch': False,
        'interval': None,
        'folder': 'root/savdb',
        'name': None,
        'error': None
    }
    parts = command_text.split()[1:]
    
    i = 0
    while i < len(parts):
        part = parts[i]
        if part == '-b':
            args['batch'] = True
            i += 1
        elif part == '-i':
            i += 1
            if i < len(parts) and parts[i].isdigit():
                args['interval'] = int(parts[i])
                i += 1
            else:
                args['error'] = "The '-i' parameter must be followed by a number."
                break
        elif part == '-m':
            i += 1
            value_parts = []
            while i < len(parts) and not parts[i].startswith('-'):
                value_parts.append(parts[i])
                i += 1
            if not value_parts:
                args['error'] = "The '-m' parameter must be followed by a folder path."
                break
            args['folder'] = " ".join(value_parts)
        elif part == '-n':
            i += 1
            value_parts = []
            while i < len(parts) and not parts[i].startswith('-'):
                value_parts.append(parts[i])
                i += 1
            if not value_parts:
                args['error'] = "The '-n' parameter must be followed by a filename."
                break
            args['name'] = " ".join(value_parts)
        else:
            args['error'] = f"Unrecognized parameter: {part}"
            break
    return args

# --- Helper function to extract media (from old script) ---
def extract_media_info(message: Message):
    media = (
        message.video or
        message.document or
        message.audio or
        message.photo or
        message.voice or
        message.animation
    )
    if not media:
        return None

    file_id = getattr(media, 'file_id', None)
    mime_type = getattr(media, 'mime_type', 'application/octet-stream')
    file_name = getattr(media, 'file_name', None)
    file_size = getattr(media, 'file_size', 0)
    thumbnail_file_id = None

    # For photos, the object itself contains multiple sizes.
    # The default file_id from pyrogram is already the largest one.
    if message.photo:
        mime_type = 'image/jpeg' # Photos from Telegram are typically jpeg
        # For photos, we use the photo's own file_id as its thumbnail.
        thumbnail_file_id = file_id 
    else:
        # For other media types, find the best quality thumbnail from the thumbs list.
        thumbs = getattr(media, 'thumbs', [])
        if thumbs:
            best_thumb = max(thumbs, key=lambda t: t.file_size)
            thumbnail_file_id = best_thumb.file_id

    if not file_name:
        ext = mimetypes.guess_extension(mime_type) or ''
        file_name = f"{file_id}{ext}"

    return file_id, file_name, mime_type, file_size, thumbnail_file_id

# --- Event Handlers (from old script) ---
@client.on_message(filters.command("savdb"))
async def save_file_id(client: Client, message: Message):
    logger.info(f"Received /savdb command from user {message.from_user.id} in chat {message.chat.id}")
    
    if not message.reply_to_message:
        usage_text = (
            "**How to use /savdb**\n\n"
            "Please reply to a message with this command.\n\n"
            "**Basic Usage:**\n"
            "- Reply to a message with a file and use `/savdb` to save it to the default folder (`root/savdb`).\n\n"
            "**Parameters:**\n"
            "- `-b`: Save a batch of files from a media group (album).\n"
            "- `-i <number>`: Save a specific number of files starting from the replied message (from old to new).\n"
            "- `-m <folder_path>`: Specify a custom folder to save the file(s) to.\n"
            "- `-n <new_name>`: Rename the file (only works for single file saving).\n\n"
            "**Examples:**\n"
            "- `/savdb -m my_videos`: Saves the replied file to `root/my_videos`.\n"
            "- `/savdb -i 5 -m homework`: Saves the next 5 files to `root/homework`.\n"
            "- `/savdb -b -m vacation_pics`: Saves all files from the replied album to `root/vacation_pics`.\n"
            "- `/savdb -n report.pdf`: Saves the replied file and renames it to `report.pdf`.\n"
        )
        await message.reply_text(usage_text, disable_web_page_preview=True)
        return

    reply_msg = message.reply_to_message
    command_text = message.text or message.caption or ""
    args = parse_custom_args(command_text)

    if args.get('error'):
        await message.reply_text(f"❌ Parameter Error: {args['error']}")
        return

    target_folder = args['folder']
    if not target_folder.startswith('root'):
        target_folder = f'root/{target_folder}'

    saved_count = 0
    failed_count = 0
    messages_to_process = []

    if args['batch']:
        try:
            media_group = await client.get_media_group(message.chat.id, reply_msg.id)
            messages_to_process.extend(media_group)
        except ValueError:
            messages_to_process.append(reply_msg)
        except Exception as e:
            await message.reply_text(f"❌ Failed to get media group: {e}")
            return
    elif args['interval']:
        target_file_count = args['interval']
        if target_file_count > 200: # Safety limit
             await message.reply_text("❌ Batch processing is limited to 200 files." )
             return

        scan_limit = min(target_file_count * 5, 1000)
        
        processing_msg = await message.reply_text(f"🔍 Scanning up to {scan_limit} messages to find {target_file_count} files...")

        try:
            message_ids = list(range(reply_msg.id, reply_msg.id + scan_limit))
            history = await client.get_messages(
                chat_id=message.chat.id,
                message_ids=message_ids,
                replies=0,
            )

            found_messages = []
            for msg in (m for m in history if m):
                if extract_media_info(msg):
                    found_messages.append(msg)
                    if len(found_messages) >= target_file_count:
                        break

            messages_to_process.extend(found_messages)

        except Exception as e:
            await processing_msg.edit_text(f"❌ Failed to get message history: {e}")
            return
    else:
        messages_to_process.append(reply_msg)

    if not messages_to_process:
        await message.reply_text("❌ No messages found to process." )
        return

    if 'processing_msg' not in locals():
        processing_msg = await message.reply_text(f"🔍 Processing {len(messages_to_process)} message(s)...")

    for msg in messages_to_process:
        media_info = extract_media_info(msg)
        if media_info:
            file_id, file_name, mime_type, file_size, thumbnail_file_id = media_info
            
            if args['name'] and not (args['batch'] or args['interval']):
                new_name = args['name']
                _, original_ext = os.path.splitext(file_name)
                _, new_ext = os.path.splitext(new_name)
                if not new_ext and original_ext:
                    file_name = new_name + original_ext
                else:
                    file_name = new_name
            
            chat_id_str = str(message.chat.id)
            if chat_id_str.startswith('-100'):
                chat_id_str = chat_id_str[4:]
            message_link = f"https://t.me/c/{chat_id_str}/{msg.id}"

            if add_file_with_folder_creation(file_name, file_id, target_folder, file_size, mime_type, thumbnail_file_id, message_link):
                saved_count += 1
            else:
                failed_count += 1
        await asyncio.sleep(0.1)

    try:
        reply_text = f"✅ Operation Complete!\n\n- **Target Folder**: `{target_folder}`\n"
        reply_text += f"- **Successfully Saved**: {saved_count} file(s)\n"
        if failed_count > 0:
            reply_text += f"- **Failed to Save**: {failed_count} file(s)\n"
        await processing_msg.edit_text(reply_text)
    except Exception as e:
        logger.error(f"Failed to edit final message: {e}")
        await message.reply_text(reply_text)

@client.on_message(filters.chat(MONITORED_CHAT_IDS) & (filters.document | filters.photo | filters.video | filters.audio) if MONITORED_CHAT_IDS else filters.chat([]))
async def handle_monitored_file(client: Client, message: Message):
    logger.info(f"Received message in monitored chat: {message.chat.id}, message_id: {message.id}")
    
    media_info = extract_media_info(message)
    if media_info:
        file_id, file_name, mime_type, file_size, thumbnail_file_id = media_info
        # Get chat title and create a safe folder name from it
        chat_title = message.chat.title if message.chat.title else str(message.chat.id)
        safe_chat_title = re.sub(r'[\\/*?:\"<>|]', "", chat_title)
        monitored_folder = f"root/monitored_files/{safe_chat_title}"
        
        logger.info(f"Adding monitored file to database: {file_name} ({file_id}) in folder {monitored_folder}")
        
        chat_id_str = str(message.chat.id)
        if chat_id_str.startswith('-100'):
            chat_id_str = chat_id_str[4:]
        message_link = f"https://t.me/c/{chat_id_str}/{message.id}"

        add_file_with_folder_creation(file_name, file_id, monitored_folder, file_size, mime_type, thumbnail_file_id, message_link)
    else:
        logger.warning(f"Could not extract file information from message: {message}")

if __name__ == "__main__":
    logger.info("Starting standalone Telegram listener...")
    client.run()
