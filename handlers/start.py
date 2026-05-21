from aiogram import Router, types, Bot
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

def get_approval_keyboard(user_id: int, som_amount: int = 500000):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Qabul qilish (500k)",
                callback_data=f"approve_student_{user_id}_500000"
            ),
            InlineKeyboardButton(
                text="✅ Qabul (800k)",
                callback_data=f"approve_student_{user_id}_800000"
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Rad etish",
                callback_data=f"reject_student_{user_id}"
            )
        ]
    ])

@router.message(CommandStart())
async def cmd_start(message: types.Message, bot: Bot):
    user = message.from_user
    is_teacher = user.id == TEACHER_ID

    args = message.text.split(maxsplit=1)
    deep_link = args[1].strip() if len(args) > 1 else ""

    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    is_new = await register_student(
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
            f"Arizangiz ustozga yuborildi.\n"
            f"Ustoz qabul qilgandan so'ng darslar ochiladi! ⏳",
            reply_markup=get_keyboard()
        )

        # Ustozga xabarnoma yuborish
        username_text = f"@{user.username}" if user.username else f"ID: {user.id}"
        try:
            await bot.send_message(
                TEACHER_ID,
                f"🔔 <b>Yangi o'quvchi!</b>\n\n"
                f"👤 <b>{full_name}</b>\n"
                f"🔗 {username_text}\n"
                f"🆔 ID: <code>{user.id}</code>\n\n"
                f"Qabul qilasizmi?",
                reply_markup=get_approval_keyboard(user.id)
            )
        except Exception as e:
            print(f"Ustoz xabarnomasi xatosi: {e}")

@router.callback_query(lambda c: c.data and c.data.startswith("approve_student_"))
async def approve_student_callback(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id != TEACHER_ID:
        await callback.answer("Bu tugma faqat ustoz uchun!", show_alert=True)
        return

    parts = callback.data.split("_")
    # approve_student_{user_id}_{som_amount}
    student_id = int(parts[2])
    som_amount = int(parts[3])

    await activate_student(student_id, som_amount)

    student = await get_student(student_id)
    full_name = student['full_name'] if student else f"ID:{student_id}"

    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ <b>Qabul qilindi!</b> ({som_amount:,} so'm)",
        reply_markup=None
    )
    await callback.answer("✅ O'quvchi qabul qilindi!")

    try:
        await bot.send_message(
            student_id,
            f"🎉 <b>Tabriklaymiz!</b>\n\n"
            f"Siz A Avlod Academy ga qabul qilindingiz!\n\n"
            f"💰 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
            f"🐮 Buzoqchangiz: <b>40 kg</b>\n"
            f"📚 1-dars testi ochiq!\n\n"
            f"Bosing va boshlang! 👇",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="🎓 Akademiyani ochish",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ]])
        )
    except Exception as e:
        print(f"O'quvchiga xabar xatosi: {e}")

@router.callback_query(lambda c: c.data and c.data.startswith("reject_student_"))
async def reject_student_callback(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id != TEACHER_ID:
        await callback.answer("Bu tugma faqat ustoz uchun!", show_alert=True)
        return

    parts = callback.data.split("_")
    student_id = int(parts[2])

    student = await get_student(student_id)
    full_name = student['full_name'] if student else f"ID:{student_id}"

    await callback.message.edit_text(
        callback.message.text + f"\n\n❌ <b>Rad etildi</b>",
        reply_markup=None
    )
    await callback.answer("❌ Rad etildi")

    try:
        await bot.send_message(
            student_id,
            f"😔 Afsuski, arizangiz rad etildi.\n\n"
            f"Qo'shimcha ma'lumot uchun ustozga murojaat qiling."
        )
    except Exception as e:
        print(f"O'quvchiga xabar xatosi: {e}")

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
