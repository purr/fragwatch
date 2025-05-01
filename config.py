import os
import sys

from dotenv import load_dotenv

from logger import logger

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found in .env file")
    sys.exit(1)

# Channel IDs
RECEIVE_CHANNEL_ID = -1002230030317
SEND_CHANNEL_ID = -1002672893933

# API endpoints
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_MESSAGE_URL = f"{TELEGRAM_API_URL}/sendMessage"
