"""Configuration for the Telegram bot."""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Timezone
TIMEZONE = os.getenv("TIMEZONE", "Europe/Paris")

# Reminder time
REMINDER_HOUR = 21
REMINDER_MINUTE = 0
