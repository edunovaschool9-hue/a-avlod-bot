import asyncio
import logging
import os

from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    BotCommand,
    BotCommandScopeDefault,
    MenuButtonWebApp,
    WebAppInfo,
)

from config import BOT_TOKEN, MINI_APP_URL
from database import init_db

from handlers.start import router as start_router
from handlers.student import router as student_router
from handlers.teacher import router as teacher_router
from handlers.homework import router as homework_router

from api import create_app


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


# Routers
dp.include_router(start_router)
dp.include_router(student_router)
dp.include_router(teacher_router)
dp.include_router(homework_router)


async def set_bot_commands():
    """
    Telegram command menu
    """

    student_commands = [
        BotCommand(command="start", description="🚀 Boshlash"),
        BotCommand(command="profile", description="👤 Profil"),
        BotCommand(command="balance", description="💰 Baytlar"),
        BotCommand(command="homework", description="📝 Uy vazifalar"),
        BotCommand(command="help", description="❓ Yordam"),
    ]

    # Student commands only
    await bot.set_my_commands(
        student_commands,
        scope=BotCommandScopeDefault()
    )

    # Mini App button
    if MINI_APP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🎓 Akademiya",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        )

        logger.info(f"✅ Mini App tugmasi o'rnatildi: {MINI_APP_URL}")


async def run_bot():
    """
    Start Telegram bot
    """

    await set_bot_commands()

    logger.info("✅ Handlerlar yuklandi")
    logger.info("🤖 Bot ishga tushdi")

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


async def run_api():
    """
    Start aiohttp API
    """

    app = create_app()

    port = int(os.getenv("PORT", 8080))

    runner = web.AppRunner(app)

    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=port
    )

    await site.start()

    logger.info(f"🌐 API server ishladi: {port}")


async def main():
    """
    Main app
    """

    logger.info("🚀 A Avlod Academy ishga tushmoqda...")

    await init_db()

    logger.info("✅ Database tayyor")

    await asyncio.gather(
        run_bot(),
        run_api()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot to'xtatildi")
