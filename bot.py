"""
🤖 A Avlod Academy Bot — asosiy fayl.
Ishga tushirish: python bot.py
"""

import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

from config import BOT_TOKEN, TEACHER_ID
from database import init_db
from handlers import start, student, teacher, homework
from api import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Mini App URL — Railway deploy qilgandan keyin o'zgartirish kerak
MINI_APP_URL = os.getenv("MINI_APP_URL", "")


async def set_bot_commands(bot: Bot):
    """Sets command menu in Telegram."""
    from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
    from aiogram.types import MenuButtonWebApp, WebAppInfo

    # Commands for students
    student_commands = [
        BotCommand(command="start", description="Boshlash"),
        BotCommand(command="balance", description="💾 Balansingiz"),
        BotCommand(command="profile", description="👤 Profilingiz"),
        BotCommand(command="homework", description="📝 Uy vazifalari"),
        BotCommand(command="history", description="📜 Bayt tarixi"),
        BotCommand(command="help", description="❓ Yordam"),
    ]

    # Commands for teacher
    teacher_commands = [
        BotCommand(command="students", description="👥 O'quvchilar ro'yxati"),
        BotCommand(command="add_bytes", description="💾 Bayt qo'shish"),
        BotCommand(command="sub_bytes", description="💸 Bayt ayirish"),
        BotCommand(command="new_hw", description="📝 Yangi vazifa"),
        BotCommand(command="stats", description="📊 Statistika"),
        BotCommand(command="help", description="❓ Yordam"),
    ]

    await bot.set_my_commands(student_commands, scope=BotCommandScopeDefault())
    await bot.set_my_commands(
        teacher_commands,
        scope=BotCommandScopeChat(chat_id=TEACHER_ID)
    )

    # Set Mini App button if URL is configured
    if MINI_APP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🎓 Akademiya",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        )
        logger.info(f"✅ Mini App tugmasi o'rnatildi: {MINI_APP_URL}")


async def run_bot():
    """Runs the Telegram bot."""
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(student.router)
    dp.include_router(teacher.router)
    dp.include_router(homework.router)

    await set_bot_commands(bot)
    logger.info("✅ Barcha handlerlar ulandi")
    logger.info("👂 Xabarlar tinglanmoqda... (Ctrl+C — to'xtatish)")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_api():
    """Runs the aiohttp API server."""
    app = create_app()
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"✅ API server ishga tushdi: http://0.0.0.0:{port}")


async def main():
    logger.info("🚀 A Avlod Academy Bot ishga tushmoqda...")
    await init_db()
    logger.info("✅ Ma'lumotlar bazasi tayyor")

    # Run bot and API together
    await asyncio.gather(
        run_bot(),
        run_api(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Bot to'xtatildi")
