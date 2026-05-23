import asyncio
import logging
import os
from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
    MenuButtonWebApp,
    WebAppInfo,
)
from config import BOT_TOKEN, MINI_APP_URL, TEACHER_ID
from database import init_db, get_pool
from handlers.start import router as start_router
from handlers.student import router as student_router
from handlers.teacher import router as teacher_router
from handlers.homework import router as homework_router
from handlers.lessons import router as lessons_router
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
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(lessons_router)
dp.include_router(homework_router)
dp.include_router(teacher_router)
dp.include_router(student_router)
dp.include_router(start_router)


async def set_bot_commands():
    student_commands = [
        BotCommand(command="start", description="🚀 Boshlash"),
        BotCommand(command="darslar", description="📚 Darslar va testlar"),
        BotCommand(command="profile", description="👤 Profil"),
        BotCommand(command="balance", description="💰 Baytlar"),
        BotCommand(command="homework", description="📝 Uy vazifalar"),
        BotCommand(command="help", description="❓ Yordam"),
    ]

    teacher_commands = [
        BotCommand(command="add_student", description="➕ O'quvchi qo'shish"),
        BotCommand(command="students", description="👥 O'quvchilar ro'yxati"),
        BotCommand(command="approve_test", description="✅ Testni tasdiqlash"),
        BotCommand(command="add_bytes", description="💾 Bayt qo'shish"),
        BotCommand(command="sub_bytes", description="💸 Bayt ayirish"),
        BotCommand(command="warn", description="⚠️ Ogohlantirish"),
        BotCommand(command="new_hw", description="📝 Yangi vazifa"),
        BotCommand(command="stats", description="📊 Statistika"),
    ]

    await bot.set_my_commands(
        student_commands,
        scope=BotCommandScopeDefault()
    )

    try:
        await bot.set_my_commands(
            teacher_commands,
            scope=BotCommandScopeChat(chat_id=TEACHER_ID)
        )
    except Exception as e:
        logger.warning(f"Teacher commands error: {e}")

    if MINI_APP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="🎓 Akademiya",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        )
        logger.info(f"✅ Mini App tugmasi o'rnatildi: {MINI_APP_URL}")


async def run_bot():
    await set_bot_commands()
    logger.info("✅ Handlerlar yuklandi")
    logger.info("🤖 Bot ishga tushdi")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_api():
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

async def _ensure_reminder_columns():
        pool = await get_pool()
        async with pool.acquire() as conn:
                    try:
                                    await conn.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS reminder_count INTEGER DEFAULT 0")
                                    await conn.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS last_reminded TIMESTAMP")
                    except Exception as e:
                                    logger.warning(f"Column migration: {e}")


async def check_inactive_students():
        while True:
                    try:
                                    await asyncio.sleep(3600)
                                    pool = await get_pool()
                                    async with pool.acquire() as conn:
                                                        rows = await conn.fetch("""
                                                                            SELECT telegram_id, full_name, reminder_count FROM students
                                                                                                WHERE is_active=1
                                                                                                                    AND last_active < NOW() - INTERVAL '4 hours'
                                                                                                                                        AND (last_reminded IS NULL OR last_reminded < NOW() - INTERVAL '4 hours')
                                                                                                                                                        """)
                                                        for s in rows:
                                                                                sid = s['telegram_id']
                                                                                name = s['full_name']
                                                                                rc = s.get('reminder_count') or 0
                                                                                try:
                                                                                                            if rc == 0:
                                                                                                                                            await bot.send_message(sid,
                                                                                                                                                                                                   f"Siz darsni unutdingiz, {name}!\n"
                                                                                                                                                                                                   f"4 soat ichida javob bermasa -5 kg jarima!")
                                                                                                                                            await conn.execute(
                                                                                                                                                                                "UPDATE students SET reminder_count=1,last_reminded=NOW() WHERE telegram_id=$1", sid)
                                                                                    elif rc == 1:
                                                                                        calf = await conn.fetchval("SELECT calf_kg FROM students WHERE telegram_id=$1", sid)
                                                                                        if calf is not None:
                                                                                                                            await conn.execute(
                                                                                                                                                                    "UPDATE students SET calf_kg=$1,reminder_count=2,last_reminded=NOW() WHERE telegram_id=$2",
                                                                                                                                                                    max(20.0, calf - 5), sid)
                                                                                                                        await bot.send_message(sid,
                                                                                                                                                                               f"OXIRGI OGOHLANTIRISH! {name}\n"
                                                                                                                                                                               f"Buzoqcha -5 kg!\nYana javob bermasangiz -10 kg va 10000 som jarima!")
                    else:
                                                    calf = await conn.fetchval("SELECT calf_kg FROM students WHERE telegram_id=$1", sid)
                                                    som = await conn.fetchval("SELECT som_balance FROM students WHERE telegram_id=$1", sid)
                                                    if calf is not None:
                                                                                        await conn.execute(
                                                                                                                                "UPDATE students SET calf_kg=$1,som_balance=$2,reminder_count=0,last_reminded=NOW() WHERE telegram_id=$3",
                                                                                                                                max(20.0, calf-10), max(0,(som or 0)-10000), sid)
                                                                                        await conn.execute(
                                                                                                                                "INSERT INTO som_transactions (student_id,amount,reason) VALUES ($1,-10000,'Dars otkazib yuborish')",
                                                                                                                                sid)
                                                                                    await bot.send_message(sid,
                                                                                                                                           f"JARIMA! {name}\n-10 kg\n-10000 som\nDarslarni bajaring!")
                                                    try:
                                                                                        await bot.send_message(TEACHER_ID, f"Jarima: {name} -10kg -10000som")
                                                    except Exception:
                                                                                        pass
                                                    except Exception as e:
                                                                                logger.error(f"Reminder {sid}: {e}")
                                                    except Exception as e:
                                                                    logger.error(f"Reminder loop: {e}")
                                                                    await asyncio.sleep(300)


async def reset_daily_reminders():
        while True:
                    try:
                                    now = datetime.now()
                                    nxt = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                                    await asyncio.sleep((nxt - now).total_seconds())
                                    pool = await get_pool()
                                    async with pool.acquire() as conn:
                                                        await conn.execute("UPDATE students SET reminder_count=0 WHERE is_active=1")
                    except Exception as e:
                                    logger.error(f"Reset: {e}")
                                    await asyncio.sleep(3600)



async def main():
    logger.info("🚀 A Avlod Academy ishga tushmoqda...")
    await init_db()
        await _ensure_reminder_columns()
    logger.info("✅ Database tayyor")
    await asyncio.gather(
        run_bot(),
        check_inactive_students(),
        reset_daily_reminders(),
        run_api()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot to'xtatildi")
