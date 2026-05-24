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
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(start_router)
dp.include_router(student_router)
dp.include_router(teacher_router)
dp.include_router(homework_router)
dp.include_router(lessons_router)


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
                           last_active, calf_kg, som_balance
                    FROM students
                    WHERE is_active = TRUE
                    AND (last_active IS NULL OR last_active < $1)
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
                            new_calf = max(0, calf_kg - 10)
                            new_balance = max(0, som_balance - 10000)
                            await conn.execute(
                                """UPDATE students SET calf_kg = $1, som_balance = $2,
                                   reminder_count = 3 WHERE telegram_id = $3""",
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

        await asyncio.sleep(4 * 60 * 60)


async def reset_daily_reminders():
    """Reset reminder_count to 0 at midnight every day for active students."""
    while True:
        try:
            now = datetime.utcnow()
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


# ─────────────────────────────────────────────
# SCHEDULE REMINDERS
# ─────────────────────────────────────────────

async def send_lesson_day_reminders():
    """Send reminder 1 day before scheduled lesson. Runs daily at 18:00 UTC+5 (13:00 UTC)."""
    while True:
        try:
            now_utc = datetime.utcnow()
            # Target: 13:00 UTC daily (18:00 Tashkent time)
            target = now_utc.replace(hour=13, minute=0, second=0, microsecond=0)
            if now_utc >= target:
                target += timedelta(days=1)
            wait_seconds = (target - now_utc).total_seconds()
            await asyncio.sleep(wait_seconds)

            # Tomorrow's day of week (UTC+5)
            tomorrow_local = datetime.utcnow() + timedelta(hours=5, days=1)
            tomorrow_dow = tomorrow_local.weekday()  # 0=Mon..6=Sun

            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT sc.student_id, sc.lesson_time, s.full_name, s.username, s.calf_kg
                    FROM schedules sc
                    JOIN students s ON s.telegram_id = sc.student_id
                    WHERE sc.day_of_week = $1 AND s.is_active = 1
                """, tomorrow_dow)

            days_uz = {0:"Dushanba",1:"Seshanba",2:"Chorshanba",3:"Payshanba",
                      4:"Juma",5:"Shanba",6:"Yakshanba"}

            for row in rows:
                try:
                    day_name = days_uz.get(tomorrow_dow, "Ertaga")
                    await bot.send_message(
                        row['student_id'],
                        f"\U0001f4c5 <b>Dars eslatmasi!</b>\n\n"
                        f"Salom {row['full_name']}! \U0001f44b\n\n"
                        f"Ertaga ({day_name}) <b>{row['lesson_time']}</b>da dars!\n\n"
                        f"\u23f0 Kechikmaslik uchun:\n"
                        f"• O'z vaqtida keling!\n"
                        f"• Kechikish yoki kelmagan holda: <b>-10 kg buzoqchadan</b>!\n\n"
                        f"\U0001f4aa Muvaffaqiyatlar!"
                    )
                except Exception as e:
                    logger.warning(f"Schedule reminder error for {row['student_id']}: {e}")

            logger.info(f"\u2705 Sent schedule reminders for {len(rows)} students (tomorrow DOW={tomorrow_dow})")

        except Exception as e:
            logger.error(f"send_lesson_day_reminders error: {e}")
            await asyncio.sleep(3600)


async def check_homework_deadline():
    """Check if students completed test+tez aytish by 20:00.
    Lesson day is X, deadline is X+1 (next day) at 20:00.
    Check runs every 2 hours after 20:00."""
    while True:
        try:
            now_local = datetime.utcnow() + timedelta(hours=5)  # Tashkent time
            current_dow = now_local.weekday()
            current_hour = now_local.hour

            # Only check after 20:00
            if current_hour >= 20:
                pool = await get_pool()
                async with pool.acquire() as conn:
                    # Get students who had lesson TODAY (before deadline 20:00)
                    rows = await conn.fetch("""
                        SELECT sc.student_id, sc.lesson_time, sc.day_of_week,
                               s.full_name, s.calf_kg, s.telegram_id
                        FROM schedules sc
                        JOIN students s ON s.telegram_id = sc.student_id
                        WHERE sc.day_of_week = $1 AND s.is_active = 1
                    """, current_dow)

                for row in rows:
                    try:
                        student_id = row['student_id']

                        # Get current lesson
                        pool3 = await get_pool()
                        async with pool3.acquire() as conn3:
                            lesson_row = await conn3.fetchrow("""
                                SELECT MAX(lesson_id) as lid FROM lesson_access
                                WHERE student_id = $1
                            """, student_id)
                            lesson_id = lesson_row['lid'] if lesson_row and lesson_row['lid'] else 1

                            # Check test done
                            test_row = await conn3.fetchrow("""
                                SELECT test_passed FROM lesson_access
                                WHERE student_id = $1 AND lesson_id = $2
                            """, student_id, lesson_id)

                            # Check tez aytish done
                            tez_row = await conn3.fetchrow("""
                                SELECT status FROM tez_aytish_access
                                WHERE student_id = $1 AND lesson_id = $2
                            """, student_id, lesson_id)

                        test_done = test_row and test_row['test_passed'] == 1
                        tez_done = tez_row and tez_row['status'] in ('done', 'pending')

                        if not test_done or not tez_done:
                            missing = []
                            if not test_done:
                                missing.append("\U0001f9ea Test")
                            if not tez_done:
                                missing.append("\U0001f3a4 Tez aytish")
                            missing_text = " va ".join(missing)

                            # Apply penalty
                            new_calf = max(0, row['calf_kg'] - 5)
                            pool2 = await get_pool()
                            async with pool2.acquire() as conn2:
                                await conn2.execute(
                                    "UPDATE students SET calf_kg = $1 WHERE telegram_id = $2",
                                    new_calf, student_id
                                )

                            await bot.send_message(
                                student_id,
                                f"\u274c <b>Dars topshiriqlarini bajarmadingiz!</b>\n\n"
                                f"Bugun dars bo'ldi, lekin 20:00gacha bajarmadingiiz:\n"
                                f"{missing_text}\n\n"
                                f"\U0001f42e Buzoqchadan <b>-5 kg</b> ayirildi!\n"
                                f"Qolgan: <b>{new_calf} kg</b>\n\n"
                                f"\U0001f4da Tezroq bajaring!"
                            )
                    except Exception as e:
                        logger.warning(f"Homework deadline check error for {row.get('student_id','?')}: {e}")

        except Exception as e:
            logger.error(f"check_homework_deadline error: {e}")

        await asyncio.sleep(2 * 60 * 60)  # every 2 hours


async def set_bot_commands():
    student_commands = [
        BotCommand(command="start", description="\U0001f680 Boshlash"),
        BotCommand(command="darslar", description="\U0001f4da Darslar va testlar"),
        BotCommand(command="tez_aytish", description="\U0001f3a4 Tez aytish kursi"),
        BotCommand(command="profile", description="\U0001f464 Profil"),
        BotCommand(command="balance", description="\U0001f4b0 Baytlar"),
        BotCommand(command="homework", description="\U0001f4dd Uy vazifalar"),
        BotCommand(command="help", description="\u2753 Yordam"),
    ]

    teacher_commands = [
        BotCommand(command="students", description="\U0001f465 O'quvchilar ro'yxati"),
        BotCommand(command="approve_test", description="\u2705 Testni tasdiqlash"),
        BotCommand(command="add_bytes", description="\U0001f4be Bayt qo'shish"),
        BotCommand(command="sub_bytes", description="\U0001f4b8 Bayt ayirish"),
        BotCommand(command="warn", description="\u26a0\ufe0f Ogohlantirish"),
        BotCommand(command="new_hw", description="\U0001f4dd Yangi vazifa"),
        BotCommand(command="stats", description="\U0001f4ca Statistika"),
        BotCommand(command="announce", description="\U0001f4e2 Barcha o'quvchilarga xabar"),
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
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
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
        send_lesson_day_reminders(),
        check_homework_deadline(),
    )

if __name__ == "__main__":
    asyncio.run(main())
