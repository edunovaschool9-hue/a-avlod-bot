from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database import register_student, get_student, activate_student
from config import TEACHER_ID, MINI_APP_URL

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    is_teacher = user.id == TEACHER_ID

    # Check activation link: /start activate_500000
    args = message.text.split(maxsplit=1)
    deep_link = args[1] if len(args) > 1 else ""

    if is_teacher:
        await message.answer(
            f"👋 Salom, ustoz {user.first_name}!\n\n"
            f"<b>Asosiy buyruqlar:</b>\n"
            f"➕ /add_student @username 500000\n"
            f"✅ /approve_test @username 1\n"
            f"👥 /students\n"
            f"⚠️ /warn @username sabab\n"
            f"💾 /add_bytes @username 50\n"
            f"📊 /stats\n\n"
            f"<b>Havola orqali faollashtirish:</b>\n"
            f"<code>t.me/a_avlod_bot?start=activate_500000</code>\n"
            f"(500000 o'rniga kerakli summani yozing)\n\n"
            f"<i>ID: {user.id}</i>"
        )
        return

    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    is_new = await register_student(
        telegram_id=user.id,
        username=user.username or "",
        full_name=full_name
    )

    # Auto-activate if deep link
    if deep_link.startswith("activate_"):
        try:
            som_amount = int(deep_link.split("_")[1])
            student = await get_student(user.id)
            if student and not student.get('is_active'):
                await activate_student(user.id, som_amount)
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🎓 Akademiyani ochish",
                        web_app=WebAppInfo(url=MINI_APP_URL)
                    )
                ]])
                await message.answer(
                    f"🎉 <b>Tabriklaymiz, {user.first_name}!</b>\n\n"
                    f"Siz A Avlod Academy ga qo'shildingiz!\n\n"
                    f"💰 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
                    f"🐮 Buzoqchangiz: <b>40 kg</b>\n"
                    f"📚 1-dars testi ochiq!\n\n"
                    f"Bosing va boshlang! 👇",
                    reply_markup=keyboard
                )
                return
            elif student and student.get('is_active'):
                await message.answer(f"Siz allaqachon faollashtirilgansiz! 👋")
                return
        except Exception:
            pass

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎓 Akademiyani ochish",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])

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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🎓 Akademiyani ochish",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])
    await message.answer(
        "<b>📚 Buyruqlar:</b>\n\n"
        "💰 /balance — bayt balansi\n"
        "👤 /profile — mening profilim\n"
        "📝 /homework — uy vazifalarim\n"
        "📜 /history — bayt tarixi\n\n"
        "Yoki pastdagi tugmani bosing 👇",
        reply_markup=keyboard
    )
