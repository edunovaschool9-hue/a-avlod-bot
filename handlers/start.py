from aiogram import Router, types, Bot, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database import register_student, get_student, activate_student, update_student_name, activate_tez_aytish_for_student
from config import TEACHER_ID, MINI_APP_URL

router = Router()

# FSM states
class Registration(StatesGroup):
        waiting_for_name = State()

class ContractStates(StatesGroup):
        waiting_payment_screenshot = State()

def get_keyboard():
        return InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                                    text="🎓 Akademiyani ochish",
                                    web_app=WebAppInfo(url=MINI_APP_URL)
                    )
        ]])

def get_main_menu_keyboard():
        return InlineKeyboardMarkup(inline_keyboard=[
                    [
                                    InlineKeyboardButton(
                                                        text="🎓 Akademiyani ochish",
                                                        web_app=WebAppInfo(url=MINI_APP_URL)
                                    )
                    ],
                    [
                                    InlineKeyboardButton(
                                                        text="📄 Shartnoma (3 oylik kurs)",
                                                        callback_data="show_contract"
                                    )
                    ]
        ])

def get_approval_keyboard(user_id: int):
        return InlineKeyboardMarkup(inline_keyboard=[
                    [
                                    InlineKeyboardButton(
                                                        text="✅ Qabul (500k)",
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

def get_contract_keyboard():
        return InlineKeyboardMarkup(inline_keyboard=[
                    [
                                    InlineKeyboardButton(text="💳 500 000 so'm", callback_data="contract_500000"),
                                    InlineKeyboardButton(text="💳 800 000 so'm", callback_data="contract_800000"),
                    ],
                    [
                                    InlineKeyboardButton(text="❌ Bekor qilish", callback_data="contract_cancel")
                    ]
        ])

def get_payment_method_keyboard(amount: int):
        return InlineKeyboardMarkup(inline_keyboard=[
                    [
                                    InlineKeyboardButton(text="💵 Naqd pul", callback_data=f"pay_cash_{amount}"),
                                    InlineKeyboardButton(text="💳 Karta", callback_data=f"pay_card_{amount}"),
                    ],
                    [
                                    InlineKeyboardButton(text="⬅️ Orqaga", callback_data="show_contract")
                    ]
        ])

def get_payment_confirm_keyboard(user_id: int, amount: int):
        return InlineKeyboardMarkup(inline_keyboard=[
                    [
                                    InlineKeyboardButton(
                                                        text="✅ To'lovni tasdiqlash",
                                                        callback_data=f"confirm_payment_{user_id}_{amount}"
                                    ),
                                    InlineKeyboardButton(
                                                        text="❌ Rad etish",
                                                        callback_data=f"reject_payment_{user_id}"
                                    )
                    ]
        ])

@router.message(CommandStart())
async def cmd_start(message: types.Message, bot: Bot, state: FSMContext):
        user = message.from_user
        is_teacher = user.id == TEACHER_ID

    args = message.text.split(maxsplit=1)
    deep_link = args[1].strip() if len(args) > 1 else ""

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
                                await activate_tez_aytish_for_student(user.id)
                                await message.answer(
                                    f"🎉 <b>Tabriklaymiz!</b>\n\n"
                                    f"A Avlod Academy ga xush kelibsiz!\n\n"
                                    f"💰 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
                                    f"🐮 Buzoqchangiz: <b>40 kg</b>\n"
                                    f"📚 1-dars testi ochiq!\n\n"
                                    f"Bosing va boshlang! 👇",
                                    reply_markup=get_main_menu_keyboard()
                                )
                                return
except Exception as e:
            print(f"Aktivatsiya xatosi: {e}")

    student = await get_student(user.id)
    if student and student.get('is_active'):
                await message.answer(
                                f"Qaytib keldingiz, {student['full_name']}! 👋\n\n"
                                f"💾 Balans: <b>{student['bytes_balance']} bayt</b>\n"
                                f"💰 Hisob: <b>{student.get('som_balance', 0):,} so'm</b>\n\n"
                                f"Akademiyaga kirish uchun bosing! 👇",
                                reply_markup=get_main_menu_keyboard()
                )
                return

    # New or pending student — ask for real name
    await state.set_state(Registration.waiting_for_name)
    await state.update_data(telegram_id=user.id, username=user.username or "")
    await message.answer(
                f"🎉 <b>A Avlod Academy</b> ga xush kelibsiz!\n\n"
                f"📝 Iltimos, <b>to'liq ismingizni</b> yozing:\n"
                f"<i>(Masalan: Aziz Karimov)</i>\n\n"
                f"⚠️ Agar bola o'qiyotgan bo'lsa — bolaning ismini yozing!"
    )

@router.message(Registration.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext, bot: Bot):
        data = await state.get_data()
        telegram_id = data.get('telegram_id', message.from_user.id)
        username = data.get('username', message.from_user.username or "")
        entered_name = message.text.strip()

    if len(entered_name) < 3 or len(entered_name) > 60:
                await message.answer(
                                "❌ Iltimos, to'g'ri ism kiriting (3-60 belgi).\n"
                                "Masalan: <b>Aziz Karimov</b>"
                )
                return

    existing = await get_student(telegram_id)
    if not existing:
                await register_student(
                                telegram_id=telegram_id,
                                username=username,
                                full_name=entered_name
                )
else:
            await update_student_name(telegram_id, entered_name)

    await state.clear()

    username_text = f"@{username}" if username else f"ID: {telegram_id}"

    await message.answer(
                f"✅ Rahmat, <b>{entered_name}</b>!\n\n"
                f"Arizangiz ustozga yuborildi.\n"
                f"Ustoz qabul qilgandan so'ng darslar ochiladi! ⏳\n\n"
                f"Shu orada shartnoma bilan tanishishingiz mumkin 👇",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                                InlineKeyboardButton(text="📄 Shartnoma ko'rish", callback_data="show_contract")
                ]])
    )

    try:
                await bot.send_message(
                                TEACHER_ID,
                                f"🔔 <b>Yangi o'quvchi arizasi!</b>\n\n"
                                f"👤 <b>{entered_name}</b>\n"
                                f"🔗 {username_text}\n"
                                f"🆔 Telegram ID: <code>{telegram_id}</code>\n\n"
                                f"Qabul qilasizmi?",
                                reply_markup=get_approval_keyboard(telegram_id)
                )
except Exception as e:
            print(f"Ustoz xabarnomasi xatosi: {e}")

# ─────────────────────────────────────────────
# SHARTNOMA (CONTRACT) HANDLERS
# ─────────────────────────────────────────────

@router.callback_query(F.data == "show_contract")
async def show_contract(callback: types.CallbackQuery):
        contract_text = (
                    "📄 <b>SHARTNOMA — 3 OYLIK KURS</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "<b>A Avlod Academy</b> bilan 3 oylik o'quv shartnomasi\n\n"
                    "📌 <b>Kurs tarkibi:</b>\n"
                    "• Oylik darslar va testlar\n"
                    "• Tez aytish mashqlari\n"
                    "• Bayt va so'm tizimi\n"
                    "• Ustoz nazorati\n\n"
                    "📌 <b>Kurs narxi (3 oy):</b>\n"
                    "• 💰 500 000 so'm — asosiy paket\n"
                    "• 💎 800 000 so'm — premium paket\n\n"
                    "📌 <b>Shartlar:</b>\n"
                    "• To'lov to'liq amalga oshiriladi\n"
                    "• Darslarni o'z vaqtida topshirish majburiy\n"
                    "• Qoidabuzarlik uchun jarima qo'llaniladi\n\n"
                    "Kurs narxini tanlang:"
        )
        await callback.message.answer(contract_text, reply_markup=get_contract_keyboard())
        await callback.answer()

@router.callback_query(F.data == "contract_cancel")
async def contract_cancel(callback: types.CallbackQuery):
        await callback.message.edit_text("❌ Shartnoma bekor qilindi.")
        await callback.answer()

@router.callback_query(F.data.startswith("contract_"))
async def contract_amount_selected(callback: types.CallbackQuery, state: FSMContext):
        if callback.data == "contract_cancel":
                    return
                amount = int(callback.data.replace("contract_", ""))
    await state.update_data(contract_amount=amount, contract_user_id=callback.from_user.id)
    text = (
                f"💳 <b>Tanlangan summa: {amount:,} so'm</b>\n\n"
                f"To'lov usulini tanlang:"
    )
    await callback.message.edit_text(text, reply_markup=get_payment_method_keyboard(amount))
    await callback.answer()

@router.callback_query(F.data.startswith("pay_cash_"))
async def pay_cash(callback: types.CallbackQuery):
        amount = int(callback.data.replace("pay_cash_", ""))
    await callback.message.edit_text(
                f"💵 <b>Naqd pul to'lovi</b>\n\n"
                f"Summa: <b>{amount:,} so'm</b>\n\n"
                f"Iltimos, naqd pulni ustoz bilan uchrashuvda to'lang.\n"
                f"To'lovdan so'ng ustoz kursni ochadi.\n\n"
                f"📞 Ustoz bilan bog'laning!"
    )
    await callback.answer()
    # Notify teacher
    try:
                from aiogram import Bot as AioBot
                from config import BOT_TOKEN
                bot = AioBot(token=BOT_TOKEN)
                student = await get_student(callback.from_user.id)
                name = student['full_name'] if student else callback.from_user.full_name
                username = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
                await bot.send_message(
                    TEACHER_ID,
                    f"💵 <b>Naqd to'lov so'rovi!</b>\n\n"
                    f"👤 {name} ({username})\n"
                    f"💰 Summa: <b>{amount:,} so'm</b>\n\n"
                    f"O'quvchi naqd pul orqali to'lashni xohlaydi."
                )
                await bot.session.close()
except Exception as e:
        print(f"Notify error: {e}")

@router.callback_query(F.data.startswith("pay_card_"))
async def pay_card(callback: types.CallbackQuery, state: FSMContext):
        amount = int(callback.data.replace("pay_card_", ""))
    await state.update_data(contract_amount=amount, contract_user_id=callback.from_user.id)
    await state.set_state(ContractStates.waiting_payment_screenshot)

    card_text = (
                f"💳 <b>Karta orqali to'lov</b>\n\n"
                f"Summa: <b>{amount:,} so'm</b>\n\n"
                f"Ushbu kartaga o'tkazing:\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏦 <b>Tilavoldiyev</b>\n"
                f"💳 <code>9860 1001 2640 9406</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"✅ To'lovdan so'ng <b>screenshot</b> yuboring!\n"
                f"(Chek rasmini shu chatga yuboring)"
    )
    await callback.message.edit_text(card_text)
    await callback.answer()

@router.message(ContractStates.waiting_payment_screenshot, F.photo)
async def receive_payment_screenshot(message: types.Message, state: FSMContext, bot: Bot):
        data = await state.get_data()
        amount = data.get('contract_amount', 0)
        user_id = message.from_user.id
        student = await get_student(user_id)
        name = student['full_name'] if student else message.from_user.full_name
        username = f"@{message.from_user.username}" if message.from_user.username else f"ID:{user_id}"

    await state.clear()

    await message.answer(
                "✅ <b>Chek qabul qilindi!</b>\n\n"
                "Ustoz to'lovni tekshiradi va kursni ochadi.\n"
                "Tez orada xabar beriladi! ⏳"
    )

    # Forward screenshot to teacher with approval buttons
    photo_id = message.photo[-1].file_id
    try:
                await bot.send_photo(
                                TEACHER_ID,
                                photo=photo_id,
                                caption=(
                                                    f"💳 <b>To'lov cheki keldi!</b>\n\n"
                                                    f"👤 {name} ({username})\n"
                                                    f"🆔 Telegram ID: <code>{user_id}</code>\n"
                                                    f"💰 Summa: <b>{amount:,} so'm</b>\n\n"
                                                    f"To'lovni tasdiqlaysizmi?"
                                ),
                                reply_markup=get_payment_confirm_keyboard(user_id, amount)
                )
except Exception as e:
            print(f"Screenshot forward error: {e}")

@router.message(ContractStates.waiting_payment_screenshot)
async def wrong_format_screenshot(message: types.Message):
        await message.answer(
                    "❌ Iltimos, <b>rasm (screenshot)</b> yuboring!\n"
                    "To'lov chekining rasmini yuboring."
        )

@router.callback_query(lambda c: c.data and c.data.startswith("confirm_payment_"))
async def confirm_payment(callback: types.CallbackQuery, bot: Bot):
        if callback.from_user.id != TEACHER_ID:
                    await callback.answer("Bu tugma faqat ustoz uchun!", show_alert=True)
                    return

        parts = callback.data.split("_")
        student_id = int(parts[2])
        amount = int(parts[3])

    await activate_student(student_id, amount)
    await activate_tez_aytish_for_student(student_id)

    student = await get_student(student_id)
    full_name = student['full_name'] if student else f"ID:{student_id}"

    await callback.message.edit_caption(
                callback.message.caption + f"\n\n✅ <b>TO'LOV TASDIQLANDI! Kurs ochildi!</b>",
                reply_markup=None
    )
    await callback.answer("✅ To'lov tasdiqlandi!")

    try:
                await bot.send_message(
                                student_id,
                                f"🎉 <b>Tabriklaymiz, {full_name}!</b>\n\n"
                                f"✅ To'lovingiz tasdiqlandi!\n"
                                f"Siz A Avlod Academy ga qabul qilindingiz!\n\n"
                                f"💰 Asosiy hisob: <b>{amount:,} so'm</b>\n"
                                f"🐮 Buzoqchangiz: <b>40 kg</b>\n"
                                f"📚 1-dars testi ochiq!\n\n"
                                f"Bosing va boshlang! 👇",
                                reply_markup=get_main_menu_keyboard()
                )
except Exception as e:
            print(f"Student notify error: {e}")

@router.callback_query(lambda c: c.data and c.data.startswith("reject_payment_"))
async def reject_payment(callback: types.CallbackQuery, bot: Bot):
        if callback.from_user.id != TEACHER_ID:
                    await callback.answer("Bu tugma faqat ustoz uchun!", show_alert=True)
                    return

        parts = callback.data.split("_")
        student_id = int(parts[2])

    student = await get_student(student_id)
    full_name = student['full_name'] if student else f"ID:{student_id}"

    await callback.message.edit_caption(
                callback.message.caption + "\n\n❌ <b>TO'LOV RAD ETILDI</b>",
                reply_markup=None
    )
    await callback.answer("❌ Rad etildi")

    try:
                await bot.send_message(
                                student_id,
                                f"😔 {full_name}, to'lovingiz tasdiqlanmadi.\n\n"
                                f"Iltimos, to'g'ri chek yuboring yoki ustoz bilan bog'laning."
                )
except Exception as e:
            print(f"Student notify error: {e}")

@router.callback_query(lambda c: c.data and c.data.startswith("approve_student_"))
async def approve_student_callback(callback: types.CallbackQuery, bot: Bot):
        if callback.from_user.id != TEACHER_ID:
                    await callback.answer("Bu tugma faqat ustoz uchun!", show_alert=True)
                    return

        parts = callback.data.split("_")
        student_id = int(parts[2])
        som_amount = int(parts[3])

    await activate_student(student_id, som_amount)
    await activate_tez_aytish_for_student(student_id)

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
                                f"🎉 <b>Tabriklaymiz, {full_name}!</b>\n\n"
                                f"Siz A Avlod Academy ga qabul qilindingiz!\n\n"
                                f"💰 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
                                f"🐮 Buzoqchangiz: <b>40 kg</b>\n"
                                f"📚 1-dars testi ochiq!\n\n"
                                f"Bosing va boshlang! 👇",
                                reply_markup=get_main_menu_keyboard()
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
                                f"😔 Afsuski, {full_name}, arizangiz rad etildi.\n\n"
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
                    reply_markup=get_main_menu_keyboard()
        )
