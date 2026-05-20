from aiogram import Router, types, Bot
from aiogram.filters import Command

from database import (
    get_all_students,
    add_bytes,
    find_student_by_username,
    activate_student,
    get_student_by_username,
    unlock_next_lesson,
    update_calf,
    add_som
)

from config import TEACHER_ID

router = Router()


def is_teacher(user_id):
    return user_id == TEACHER_ID


@router.message(Command("add_student"))
async def cmd_add_student(message: types.Message, bot: Bot):
    if not is_teacher(message.from_user.id):
        await message.answer("Bu buyruq faqat ustoz uchun.")
        return

    parts = message.text.split(maxsplit=3)

    if len(parts) < 3:
        await message.answer(
            "Noto'g'ri format.\n\n"
            "<b>Ishlatish:</b>\n"
            "<code>/add_student @username 500000</code>\n\n"
            "500000 — kurs narxi (so'm)"
        )
        return

    username = parts[1].lstrip('@')

    try:
        som_amount = int(parts[2])
    except ValueError:
        await message.answer("Summa son bolishi kerak.")
        return

    student = await get_student_by_username(username)

    if not student:
        await message.answer(
            f"@{username} topilmadi.\n"
            f"O'quvchi avval /start bosishi kerak."
        )
        return

    await activate_student(student['telegram_id'], som_amount)

    await message.answer(
        f"✅ <b>O'quvchi faollashtirildi!</b>\n\n"
        f"👤 {student['full_name']} (@{username})\n"
        f"💰 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
        f"🐮 Buzoqcha: <b>40 kg</b>\n"
        f"📚 1-dars testi ochildi\n\n"
        f"O'quvchiga xabar yuborildi!"
    )

    try:
        await bot.send_message(
            student['telegram_id'],
            f"🎉 <b>A Avlod Academy ga xush kelibsiz!</b>\n\n"
            f"Sizning hisobingiz faollashtirildi!\n\n"
            f"💰 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
            f"🐮 Buzoqchangiz: <b>40 kg</b>\n"
            f"📚 1-dars testi ochiq!\n\n"
            f"Akademiyani oching va boshlang! 🚀"
        )
    except Exception:
        pass


@router.message(Command("approve_test"))
async def cmd_approve_test(message: types.Message, bot: Bot):

    if not is_teacher(message.from_user.id):
        await message.answer("Bu buyruq faqat ustoz uchun.")
        return

    parts = message.text.split()

    if len(parts) < 3:
        await message.answer(
            "<code>/approve_test @username 1</code>\n"
            "(username va lesson_id)"
        )
        return

    username = parts[1].lstrip('@')

    try:
        lesson_id = int(parts[2])
    except ValueError:
        await message.answer("Dars raqami son bolishi kerak.")
        return

    student = await get_student_by_username(username)

    if not student:
        await message.answer(f"@{username} topilmadi.")
        return

    bytes_earned = 25

    await add_bytes(
        student['telegram_id'],
        bytes_earned,
        f"{lesson_id}-dars testi"
    )

    await update_calf(student['telegram_id'], 1.0)

    await unlock_next_lesson(student['telegram_id'], lesson_id)

    await message.answer(
        f"✅ {lesson_id}-dars testi tasdiqlandi!\n"
        f"👤 {student['full_name']}\n"
        f"+{bytes_earned} bayt, +1 kg\n"
        f"{lesson_id + 1}-dars testi ochildi"
    )

    try:
        await bot.send_message(
            student['telegram_id'],
            f"🎉 <b>Test tasdiqlandi!</b>\n\n"
            f"📚 {lesson_id}-dars testi\n"
            f"💾 <b>+{bytes_earned} bayt</b>\n"
            f"🐮 Buzoqcha <b>+1 kg</b> oldi!\n\n"
            f"📖 {lesson_id + 1}-dars testi endi ochiq!\n"
            f"Akademiyani oching! 🚀"
        )
    except Exception:
        pass


@router.message(Command("warn"))
async def cmd_warn(message: types.Message, bot: Bot):

    if not is_teacher(message.from_user.id):
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 2:
        await message.answer(
            "<code>/warn @username sabab</code>"
        )
        return

    username = parts[1].lstrip('@')

    reason = (
        parts[2]
        if len(parts) > 2
        else "Vazifa bajarilmadi"
    )

    student = await get_student_by_username(username)

    if not student:
        await message.answer(f"@{username} topilmadi.")
        return

    warnings = student.get('warnings', 0) + 1

    if warnings == 1:
        kg_penalty = 5
        som_penalty = 0
    else:
        kg_penalty = 10
        som_penalty = 10000

    await update_calf(
        student['telegram_id'],
        -kg_penalty
    )

    if som_penalty:
        await add_som(
            student['telegram_id'],
            -som_penalty,
            f"Jarima: {reason}"
        )

    from database import add_warning

    await add_warning(student['telegram_id'])

    penalty_text = (
        f"💰 -{som_penalty:,} so'm jarima"
        if som_penalty
        else ""
    )

    await message.answer(
        f"⚠️ Ogohlantirish #{warnings}\n"
        f"👤 {student['full_name']}\n"
        f"🐮 -{kg_penalty} kg\n"
        f"{penalty_text}"
    )

    try:
        msg = (
            f"⚠️ <b>Ogohlantirish #{warnings}</b>\n\n"
            f"Sabab: {reason}\n"
            f"🐮 Buzoqcha -{kg_penalty} kg yo'qotdi"
        )

        if som_penalty:
            msg += f"\n💰 -{som_penalty:,} so'm jarima"

        await bot.send_message(
            student['telegram_id'],
            msg
        )

    except Exception:
        pass
