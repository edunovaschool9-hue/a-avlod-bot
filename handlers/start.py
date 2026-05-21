from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database import register_student, get_student, activate_student
from config import TEACHER_ID, MINI_APP_URL

router = Router()


def get_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎓 Akademiyani ochish",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    is_teacher = user.id == TEACHER_ID

    args = message.text.split(maxsplit=1)
    deep_link = args[1].strip() if len(args) > 1 else ""

    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    await register_student(
        telegram_id=user.id,
        username=user.username or "",
        full_name=full_name
    )

    if is_teacher:
        await message.answer(
            f"👋 Salom, ustoz {user.first_name}!\n\n"
            f"<b>Buyruqlar:</b>\n"
            f"/add_student @username 500000\n"
            f"/approve_test @username 1\n"
            f"/students\n"
            f"/warn @username sabab\n"
            f"/add_bytes @username 50\n"
            f"/stats\n\n"
            f"<b>Aktivatsiya havolalari:</b>\n"
            f"500k: <code>https://t.me/a_avlod_bot?start=activate_500000</code>\n"
            f"800k: <code>https://t.me/a_avlod_bot?start=activate_800000</code>\n\n"
            f"<i>ID: {user.id}</i>"
        )
        return

    if deep_link.startswith("activate_"):
        try:
            som_amount = int(deep_link.replace("activate_", ""))
            await activate_student(user.id, som_amount)
            await message.answer(
                f"🎉 <b>Tabriklaymiz, {user.first_name}!</b>\n\n"
                f"A Avlod Academy ga xush kelibsiz!\n\n"
                f"💰 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
                f"🐮 Buzoqchangiz: <b>40 kg</b>\n"
                f"📚 1-dars testi ochiq!\n\n"
                f"Bosing va boshlang! 👇",
                reply_markup=get_keyboard()
            )
            return
        except Exception as e:
            print(f"Aktivatsiya xatosi: {e}")

    student = await get_student(user.id)
    if student and student.get('is_active'):
        await message.answer(
            f"Qaytib keldingiz, {user.first_name}! 👋\n\n"
            f"💾 Balans: <b>{student['bytes_balance']} bayt</b>\n"
            f"💰 Hisob: <b>{student.get('som_balance', 0):,} so'm</b>\n\n"
            f"Akademiyaga kirish uchun bosing! 👇",
            reply_markup=get_keyboard()
        )
    else:
        await message.answer(
            f"🎉 <b>A Avlod Academy</b> ga xush kelibsiz, {user.first_name}!\n\n"
            f"Kursga kirish uchun ustozdan havola oling.\n\n"
            f"Akademiyani ochib ko'rishingiz mumkin 👇",
            reply_markup=get_keyboard()
        )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "<b>📚 Buyruqlar:</b>\n\n"
        "💰 /balance — bayt balansi\n"
        "👤 /profile — mening profilim\n"
        "📝 /homework — uy vazifalarim\n\n"
        "Yoki pastdagi tugmani bosing 👇",
        reply_markup=get_keyboard()
    )
