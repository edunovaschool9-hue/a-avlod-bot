"""
Файл с настройками бота.
Здесь хранятся токен бота и ID учителя.
ВАЖНО: Этот файл НЕ должен попадать на GitHub — он в .gitignore
"""

import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env
load_dotenv()

# Токен от BotFather (хранится в .env файле)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Telegram ID учителя (твой ID)
# Как узнать: напиши боту @userinfobot — он покажет твой ID
TEACHER_ID = int(os.getenv("TEACHER_ID", "0"))

# Путь к базе данных
DATABASE_PATH = "byte_academy.db"

# Стартовый баланс новых учеников
DEFAULT_BALANCE = 0

# Проверка что всё настроено
if not BOT_TOKEN:
    raise ValueError(
        "❌ Не указан BOT_TOKEN в файле .env\n"
        "Создай файл .env по примеру .env.example"
    )

if not TEACHER_ID:
    raise ValueError(
        "❌ Не указан TEACHER_ID в файле .env\n"
        "Узнай свой ID у @userinfobot и добавь в .env"
    )
