from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database import register_student, get_student
from config import TEACHER_ID, MINI_APP_URL

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    is_teacher = user.id == TEACHER_ID

    if is_teacher:
        await message.answer(
            f"👋 Salom, ustoz {user.first_name}!\n\n"
            f"<b>Mavjud buyruqlar:</b>\n"
            f"📊 /students — barcha o'quvchilar ro'yxati\n"
            f"💾 /add_bytes @username 50 sabab — bayt qo'shish\n"
            f"💸 /sub_bytes @username 20 sabab — bayt ayirish\n"
            f"📝 /new_hw — yangi uy vazifasi berish\n"
            f"📈 /stats — umumiy statistika\n\n"
            f"<i>Sizning ID: {user.id}</i>"
        )
        return

    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    is_new = await register_student(
        telegram_id=user.id,
        username=user.username or "",
        full_name=full_name
    )

    # Кнопка открытия Mini App
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎓 Akademiyani ochish",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )]
    ])

    if is_new:
        await message.answer(
            f"🎉 <b>A Avlod Academy</b> ga xush kelibsiz, {user.first_name}!\n\n"
            f"Bu yerda siz:\n"
            f"  • Darslarni o'qib testlar topshirasiz 🧪\n"
            f"  • <b>Bayt</b> 💾 ishlaysiz\n"
            f"  • Baytlarni sovg'alarga almashtirasiz 🎁\n\n"
            f"Bosing va akademiyaga kiring! 👇",
            reply_markup=keyboard
        )
    else:
        student = await get_student(user.id)
        await message.answer(
            f"Qaytib keldingiz, {user.first_name}! 👋\n\n"
            f"💾 Balans: <b>{student['bytes_balance']} bayt</b>\n"
            f"🎖 Daraja: {student['rank']} · {student['level']}\n\n"
            f"Akademiyaga kirish uchun bosing! 👇",
            reply_markup=keyboard
        )


@router.message(lambda msg: msg.text == "/help")
async def cmd_help(message: types.Message):
    is_teacher = message.from_user.id == TEACHER_ID

    if is_teacher:
        await message.answer(
            "<b>📚 Ustoz buyruqlari:</b>\n\n"
            "📊 /students — o'quvchilar ro'yxati\n"
            "💾 /add_bytes @username 50 sabab — bayt qo'shish\n"
            "💸 /sub_bytes @username 20 sabab — bayt ayirish\n"
            "📝 /new_hw — uy vazifasi berish\n"
            "📈 /stats — umumiy statistika"
        )
    else:
        from aiogram.types import WebAppInfo
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎓 Akademiyani ochish",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )]
        ])
        await message.answer(
            "<b>📚 Buyruqlar:</b>\n\n"
            "💰 /balance — bayt balansi\n"
            "👤 /profile — mening profilim\n"
            "📝 /homework — uy vazifalarim\n"
            "📜 /history — bayt tarixi\n\n"
            "Yoki pastdagi tugmani bosing 👇",
            reply_markup=keyboard
        )
