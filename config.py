import os
from dotenv import load_dotenv

load_dotenv()

# Telegram bot
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Teacher ID
TEACHER_ID = int(os.getenv("TEACHER_ID", "0"))

# Mini App URL
MINI_APP_URL = os.getenv("MINI_APP_URL")

# Database
DATABASE_PATH = "byte_academy.db"

# Default balance
DEFAULT_BALANCE = 0
