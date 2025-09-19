import os # 導入 os 模組，用於操作環境變量
from dotenv import load_dotenv # 從 dotenv 導入 load_dotenv 函數，用於從 .env 文件加載環境變量

# Explicitly load the .env file from the /app directory inside the container
dotenv_path = '/app/.env'
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"Warning: .env file not found at {dotenv_path}")


# Database configuration
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "telegram_drive")
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Telegram 相關配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") # 從環境變量獲取 Telegram Bot Token
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") # 從環境變量獲取 Telegram 聊天 ID
API_ID = os.getenv("API_ID") # 從環境變量獲取 Telegram API ID
API_HASH = os.getenv("API_HASH") # 從環境變量獲取 Telegram API Hash
BOT_API_UPLOAD_LIMIT = 48 * 1024 * 1024 # 48 MB
MONITORED_CHAT_ID = os.getenv("MONITORED_CHAT_ID") # 從環境變量獲取監控的聊天 ID

# 緩存配置
CACHE_CLEANUP_INTERVAL_MINUTES = int(os.getenv("CACHE_CLEANUP_INTERVAL_MINUTES", 60)) # 從環境變量獲取緩存清理間隔（分鐘），默認為 60 分鐘
CACHE_MAX_SIZE_GB = float(os.getenv("CACHE_MAX_SIZE_GB", 2.0)) # 從環境變量獲取緩存最大大小（GB），默認為 2.0 GB
CACHE_MAX_AGE_MINUTES = int(os.getenv("CACHE_MAX_AGE_MINUTES", 10)) # 從環境變量獲取緩存最大存活時間（分鐘），默認為 10 分鐘

# 管理員憑據配置
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin") # 從環境變量獲取管理員用戶名，默認為 "admin"
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password") # 從環境變量獲取管理員密碼，默認為 "password"
