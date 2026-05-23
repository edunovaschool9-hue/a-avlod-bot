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

# ─────────────────────────────────────────────
# REMINDER SYSTEM (4-hour inactivity)
# ─────────────────────────────────────────────

async def check_inactive_students():
    """Check for inactive students and send reminders/penalties every 4 hours."""
    while True:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                now = datetime.utcnow()
                four_hours_ago = now - timedelta(hours=4)

                students = await conn.fetch(
                    """
                    SELECT telegram_id, full_name, reminder_count,
                           last_activity, calf_kg, som_balance
                    FROM students
                    WHERE is_active = TRUE
                    AND (last_activity IS NULL OR last_activity < $1)
                    """,
                    four_hours_ago
                )

                for student in students:
                    telegram_id = student['telegram_id']
                    full_name = student['full_name']
                    reminder_count = student.get('reminder_count', 0) or 0
                    calf_kg = student.get('calf_kg', 40) or 40
                    som_balance = student.get('som_balance', 0) or 0

                    try:
                        if reminder_count == 0:
                            # First reminder - just warning
                            await bot.send_message(
                                telegram_id,
                                f"\u23f0 <b>Eslatma!</b>\n\n"
                                f"Salom {full_name}! \U0001f44b\n"
                                f"4 soat davomida dars qilmadingiz.\n\n"
                                f"\U0001f4da Akademiyani oching va mashq qiling!\n"
                                f"\u26a0\ufe0f Keyingi eslatmada buzoqcha -5 kg yo'qotadi!"
                            )
                            await conn.execute(
                                "UPDATE students SET reminder_count = 1 WHERE telegram_id = $1",
                                telegram_id
                            )

                        elif reminder_count == 1:
                            # Second reminder - -5 kg penalty
                            new_calf = max(0, calf_kg - 5)
                            await conn.execute(
                                "UPDATE students SET calf_kg = $1, reminder_count = 2 WHERE telegram_id = $2",
                                new_calf, telegram_id
                            )
                            await bot.send_message(
                                telegram_id,
                                f"\u26a0\ufe0f <b>Oxirgi ogohlantirish!</b>\n\n"
                                f"{full_name}, 8 soat dars qilmadingiz!\n\n"
                                f"\U0001f42e Buzoqchadan <b>-5 kg</b> ayirildi!\n"
                                f"Qolgan: <b>{new_calf} kg</b>\n\n"
                                f"\U0001f6a8 Agar yana 4 soat o'tsa:\n"
                                f"• -10 kg buzoqchadan\n"
                                f"• -10 000 so'm hisobdan"
                            )

                        elif reminder_count >= 2:
                            # Third reminder - -10 kg + fine
                            new_calf = max(0, calf_kg - 10)
                            new_balance = max(0, som_balance - 10000)
                            await conn.execute(
                                """UPDATE students
                                SET calf_kg = $1, som_balance = $2, reminder_count = 3
                                WHERE telegram_id = $3""",
                                new_calf, new_balance, telegram_id
                            )
                            await bot.send_message(
                                telegram_id,
                                f"\U0001f6a8 <b>JARIMA QOYLANDI!</b>\n\n"
                                f"{full_name}, 12 soat dars qilmadingiz!\n\n"
                                f"\U0001f42e Buzoqchadan <b>-10 kg</b> ayirildi!\n"
                                f"\U0001f4b0 Hisobdan <b>-10 000 so'm</b> jarima!\n\n"
                                f"Buzoqcha: <b>{new_calf} kg</b>\n"
                                f"Hisob: <b>{new_balance:,} so'm</b>\n\n"
                                f"\U0001f4da Iltimos, darslarni bajarishni boshlang!"
                            )

                    except Exception as e:
                        logger.warning(f"Reminder error for {telegram_id}: {e}")

        except Exception as e:
            logger.error(f"check_inactive_students error: {e}")

        # Run every 4 hours
        await asyncio.sleep(4 * 60 * 60)


async def reset_daily_reminders():
    """Reset reminder_count to 0 at midnight every day for active students."""
    while True:
        try:
            now = datetime.utcnow()
            # Calculate seconds until next midnight UTC
            tomorrow = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            wait_seconds = (tomorrow - now).total_seconds()
            await asyncio.sleep(wait_seconds)

            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE students SET reminder_count = 0 WHERE is_active = TRUE"
                )
            logger.info("\u2705 Daily reminder counts reset")

        except Exception as e:
            logger.error(f"reset_daily_reminders error: {e}")
            await asyncio.sleep(3600)


async def set_bot_commands():
    student_commands = [
        BotCommand(command="start", description="\U0001f680 Boshlash"),
        BotCommand(command="darslar", description="\U0001f4da Darslar va testlar"),
        BotCommand(command="profile", description="\U0001f464 Profil"),
        BotCommand(command="balance", description="\U0001f4b0 Baytlar"),
        BotCommand(command="homework", description="\U0001f4dd Uy vazifalar"),
        BotCommand(command="help", description="\u2753 Yordam"),
    ]

    teacher_commands = [
        BotCommand(command="add_student", description="\u2795 O'quvchi qo'shish"),
        BotCommand(command="students", description="\U0001f465 O'quvchilar ro'yxati"),
        BotCommand(command="approve_test", description="\u2705 Testni tasdiqlash"),
        BotCommand(command="add_bytes", description="\U0001f4be Bayt qo'shish"),
        BotCommand(command="sub_bytes", description="\U0001f4b8 Bayt ayirish"),
        BotCommand(command="warn", description="\u26a0\ufe0f Ogohlantirish"),
        BotCommand(command="new_hw", description="\U0001f4dd Yangi vazifa"),
        BotCommand(command="stats", description="\U0001f4ca Statistika"),
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
                text="\U0001f393 Akademiya",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        )
        logger.info(f"\u2705 Mini App tugmasi o'rnatildi: {MINI_APP_URL}")

async def run_bot():
    await set_bot_commands()
    logger.info("\u2705 Handlerlar yuklandi")
    logger.info("\U0001f916 Bot ishga tushdi")
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
    logger.info(f"\U0001f310 API server ishladi: {port}")

async def main():
    logger.info("\U0001f680 A Avlod Academy ishga tushmoqda...")
    await init_db()
    logger.info("\u2705 Database tayyor")
    await asyncio.gather(
        run_bot(),
        run_api(),
        check_inactive_students(),
        reset_daily_reminders(),
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("\U0001f6d1 Bot to'xtatildi")
