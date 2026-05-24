from aiogram import Router, types, Bot, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from database import register_student, get_student, activate_student, update_student_name, activate_tez_aytish_for_student, get_all_students
from config import TEACHER_ID, MINI_APP_URL

router = Router()

# FSM states
class Registration(StatesGroup):
    waiting_for_name = State()

class ContractStates(StatesGroup):
    waiting_payment_screenshot = State()

class BroadcastStates(StatesGroup):
    waiting_message = State()

def get_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="\U0001f393 Akademiyani ochish",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])

def get_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="\U0001f393 Akademiyani ochish",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ],
        [
            InlineKeyboardButton(
                text="\U0001f4c4 Shartnoma (3 oylik kurs)",
                callback_data="show_contract"
            )
        ]
    ])

def get_approval_keyboard(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="\u2705 Qabul (500k)",
                callback_data=f"approve_student_{user_id}_500000"
            ),
            InlineKeyboardButton(
                text="\u2705 Qabul (800k)",
                callback_data=f"approve_student_{user_id}_800000"
            ),
        ],
        [
            InlineKeyboardButton(
                text="\u274c Rad etish",
                callback_data=f"reject_student_{user_id}"
            )
        ]
    ])

def get_contract_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="\U0001f4b3 500 000 so'm", callback_data="contract_500000"),
            InlineKeyboardButton(text="\U0001f4b3 800 000 so'm", callback_data="contract_800000"),
        ],
        [
            InlineKeyboardButton(text="\u274c Bekor qilish", callback_data="contract_cancel")
        ]
    ])

def get_payment_method_keyboard(amount: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="\U0001f4b5 Naqd pul", callback_data=f"pay_cash_{amount}"),
            InlineKeyboardButton(text="\U0001f4b3 Karta", callback_data=f"pay_card_{amount}"),
        ],
        [
            InlineKeyboardButton(text="\u2b05\ufe0f Orqaga", callback_data="show_contract")
        ]
    ])

def get_payment_confirm_keyboard(user_id: int, amount: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="\u2705 To'lovni tasdiqlash",
                callback_data=f"confirm_payment_{user_id}_{amount}"
            ),
            InlineKeyboardButton(
                text="\u274c Rad etish",
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
        teacher_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="\U0001f4cb  O'quvchilar ro'yxati",
                callback_data="teacher_students"
            )],
            [InlineKeyboardButton(
                text="\U0001f4e2  Barcha o'quvchilarga xabar",
                callback_data="teacher_broadcast"
            )],
        ])
        await message.answer(
            f"\U0001f44b Salom, <b>ustoz {user.first_name}</b>!\n\n"
            f"\U0001f3eb <b>A Avlod Academy</b> boshqaruv paneli\n\n"
            f"Kerakli bo'limni tanlang \U0001f447",
            reply_markup=teacher_keyboard
        )
        returnreturn

    if deep_link.startswith("activate_"):
        try:
            som_amount = int(deep_link.replace("activate_", ""))
            await activate_student(user.id, som_amount)
            await activate_tez_aytish_for_student(user.id)
            await message.answer(
                f"\U0001f389 <b>Tabriklaymiz!</b>\n\n"
                f"A Avlod Academy ga xush kelibsiz!\n\n"
                f"\U0001f4b0 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
                f"\U0001f42e Buzoqchangiz: <b>40 kg</b>\n"
                f"\U0001f4da 1-dars testi ochiq!\n\n"
                f"Bosing va boshlang! \U0001f447",
                reply_markup=get_main_menu_keyboard()
            )
            return
        except Exception as e:
            print(f"Aktivatsiya xatosi: {e}")

    student = await get_student(user.id)
    if student and student.get('is_active'):
        # ✅ Ensure tez aytish access is available for existing students
        await activate_tez_aytish_for_student(user.id)
        await message.answer(
            f"Qaytib keldingiz, {student['full_name']}! \U0001f44b\n\n"
            f"\U0001f4be Balans: <b>{student['bytes_balance']} bayt</b>\n"
            f"\U0001f4b0 Hisob: <b>{student.get('som_balance', 0):,} so'm</b>\n\n"
            f"Akademiyaga kirish uchun bosing! \U0001f447",
            reply_markup=get_main_menu_keyboard()
        )
        return

    await state.set_state(Registration.waiting_for_name)
    await state.update_data(telegram_id=user.id, username=user.username or "")
    await message.answer(
        f"\U0001f389 <b>A Avlod Academy</b> ga xush kelibsiz!\n\n"
        f"\U0001f4dd Iltimos, <b>to'liq ismingizni</b> yozing:\n"
        f"<i>(Masalan: Aziz Karimov)</i>\n\n"
        f"\u26a0\ufe0f Agar bola o'qiyotgan bo'lsa — bolaning ismini yozing!"
    )

@router.message(Registration.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    telegram_id = data.get('telegram_id', message.from_user.id)
    username = data.get('username', message.from_user.username or "")
    entered_name = message.text.strip()

    if len(entered_name) < 3 or len(entered_name) > 60:
        await message.answer(
            "\u274c Iltimos, to'g'ri ism kiriting (3-60 belgi).\n"
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
        f"\u2705 Rahmat, <b>{entered_name}</b>!\n\n"
        f"Arizangiz ustozga yuborildi.\n"
        f"Ustoz qabul qilgandan so'ng darslar ochiladi! \u23f3\n\n"
        f"Shu orada shartnoma bilan tanishishingiz mumkin \U0001f447",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="\U0001f4c4 Shartnoma ko'rish", callback_data="show_contract")
        ]])
    )

    try:
        await bot.send_message(
            TEACHER_ID,
            f"\U0001f514 <b>Yangi o'quvchi arizasi!</b>\n\n"
            f"\U0001f464 <b>{entered_name}</b>\n"
            f"\U0001f517 {username_text}\n"
            f"\U0001f194 Telegram ID: <code>{telegram_id}</code>\n\n"
            f"Qabul qilasizmi?",
            reply_markup=get_approval_keyboard(telegram_id)
        )
    except Exception as e:
        print(f"Ustoz xabarnomasi xatosi: {e}")

@router.callback_query(F.data == "show_contract")
async def show_contract(callback: types.CallbackQuery):
    contract_text = (
        "\U0001f4c4 <b>SHARTNOMA — 3 OYLIK KURS</b>\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        "<b>A Avlod Academy</b> bilan 3 oylik o'quv shartnomasi\n\n"
        "\U0001f4cc <b>Kurs tarkibi:</b>\n"
        "• Oylik darslar va testlar\n"
        "• Tez aytish mashqlari\n"
        "• Bayt va so'm tizimi\n"
        "• Ustoz nazorati\n\n"
        "\U0001f4cc <b>Kurs narxi (3 oy):</b>\n"
        "• \U0001f4b0 500 000 so'm — asosiy paket\n"
        "• \U0001f48e 800 000 so'm — premium paket\n\n"
        "\U0001f4cc <b>Shartlar:</b>\n"
        "• To'lov to'liq amalga oshiriladi\n"
        "• Darslarni o'z vaqtida topshirish majburiy\n"
        "• Qoidabuzarlik uchun jarima qo'llaniladi\n\n"
        "Kurs narxini tanlang:"
    )
    await callback.message.answer(contract_text, reply_markup=get_contract_keyboard())
    await callback.answer()

@router.callback_query(F.data == "contract_cancel")
async def contract_cancel(callback: types.CallbackQuery):
    await callback.message.edit_text("\u274c Shartnoma bekor qilindi.")
    await callback.answer()

@router.callback_query(F.data.startswith("contract_"))
async def contract_amount_selected(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "contract_cancel":
        return
    amount = int(callback.data.replace("contract_", ""))
    await state.update_data(contract_amount=amount, contract_user_id=callback.from_user.id)
    text = (
        f"\U0001f4b3 <b>Tanlangan summa: {amount:,} so'm</b>\n\n"
        f"To'lov usulini tanlang:"
    )
    await callback.message.edit_text(text, reply_markup=get_payment_method_keyboard(amount))
    await callback.answer()

@router.callback_query(F.data.startswith("pay_cash_"))
async def pay_cash(callback: types.CallbackQuery):
    amount = int(callback.data.replace("pay_cash_", ""))
    await callback.message.edit_text(
        f"\U0001f4b5 <b>Naqd pul to'lovi</b>\n\n"
        f"Summa: <b>{amount:,} so'm</b>\n\n"
        f"Iltimos, naqd pulni ustoz bilan uchrashuvda to'lang.\n"
        f"To'lovdan so'ng ustoz kursni ochadi.\n\n"
        f"\U0001f4de Ustoz bilan bog'laning!"
    )
    await callback.answer()
    try:
        from aiogram import Bot as AioBot
        from config import BOT_TOKEN
        bot_tmp = AioBot(token=BOT_TOKEN)
        student = await get_student(callback.from_user.id)
        name = student['full_name'] if student else callback.from_user.full_name
        username = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
        await bot_tmp.send_message(
            TEACHER_ID,
            f"\U0001f4b5 <b>Naqd to'lov so'rovi!</b>\n\n"
            f"\U0001f464 {name} ({username})\n"
            f"\U0001f4b0 Summa: <b>{amount:,} so'm</b>\n\n"
            f"O'quvchi naqd pul orqali to'lashni xohlaydi."
        )
        await bot_tmp.session.close()
    except Exception as e:
        print(f"Notify error: {e}")

@router.callback_query(F.data.startswith("pay_card_"))
async def pay_card(callback: types.CallbackQuery, state: FSMContext):
    amount = int(callback.data.replace("pay_card_", ""))
    await state.update_data(contract_amount=amount, contract_user_id=callback.from_user.id)
    await state.set_state(ContractStates.waiting_payment_screenshot)

    card_text = (
        f"\U0001f4b3 <b>Karta orqali to'lov</b>\n\n"
        f"Summa: <b>{amount:,} so'm</b>\n\n"
        f"Ushbu kartaga o'tkazing:\n"
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"\U0001f3e6 <b>Tilavoldiyev</b>\n"
        f"\U0001f4b3 <code>9860 1001 2640 9406</code>\n"
        f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n\n"
        f"\u2705 To'lovdan so'ng <b>screenshot</b> yuboring!\n"
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
        "\u2705 <b>Chek qabul qilindi!</b>\n\n"
        "Ustoz to'lovni tekshiradi va kursni ochadi.\n"
        "Tez orada xabar beriladi! \u23f3"
    )

    photo_id = message.photo[-1].file_id
    try:
        await bot.send_photo(
            TEACHER_ID,
            photo=photo_id,
            caption=(
                f"\U0001f4b3 <b>To'lov cheki keldi!</b>\n\n"
                f"\U0001f464 {name} ({username})\n"
                f"\U0001f194 Telegram ID: <code>{user_id}</code>\n"
                f"\U0001f4b0 Summa: <b>{amount:,} so'm</b>\n\n"
                f"To'lovni tasdiqlaysizmi?"
            ),
            reply_markup=get_payment_confirm_keyboard(user_id, amount)
        )
    except Exception as e:
        print(f"Screenshot forward error: {e}")

@router.message(ContractStates.waiting_payment_screenshot)
async def wrong_format_screenshot(message: types.Message):
    await message.answer(
        "\u274c Iltimos, <b>rasm (screenshot)</b> yuboring!\n"
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
        callback.message.caption + f"\n\n\u2705 <b>TO'LOV TASDIQLANDI! Kurs ochildi!</b>",
        reply_markup=None
    )
    await callback.answer("\u2705 To'lov tasdiqlandi!")

    try:
        await bot.send_message(
            student_id,
            f"\U0001f389 <b>Tabriklaymiz, {full_name}!</b>\n\n"
            f"\u2705 To'lovingiz tasdiqlandi!\n"
            f"Siz A Avlod Academy ga qabul qilindingiz!\n\n"
            f"\U0001f4b0 Asosiy hisob: <b>{amount:,} so'm</b>\n"
            f"\U0001f42e Buzoqchangiz: <b>40 kg</b>\n"
            f"\U0001f4da 1-dars testi ochiq!\n\n"
            f"Bosing va boshlang! \U0001f447",
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
        callback.message.caption + "\n\n\u274c <b>TO'LOV RAD ETILDI</b>",
        reply_markup=None
    )
    await callback.answer("\u274c Rad etildi")

    try:
        await bot.send_message(
            student_id,
            f"\U0001f614 {full_name}, to'lovingiz tasdiqlanmadi.\n\n"
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
        callback.message.text + f"\n\n\u2705 <b>Qabul qilindi!</b> ({som_amount:,} so'm)",
        reply_markup=None
    )
    await callback.answer("\u2705 O'quvchi qabul qilindi!")

    try:
        await bot.send_message(
            student_id,
            f"\U0001f389 <b>Tabriklaymiz, {full_name}!</b>\n\n"
            f"Siz A Avlod Academy ga qabul qilindingiz!\n\n"
            f"\U0001f4b0 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
            f"\U0001f42e Buzoqchangiz: <b>40 kg</b>\n"
            f"\U0001f4da 1-dars testi ochiq!\n\n"
            f"Bosing va boshlang! \U0001f447",
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
        callback.message.text + f"\n\n\u274c <b>Rad etildi</b>",
        reply_markup=None
    )
    await callback.answer("\u274c Rad etildi")
h
    try:
        await bot.send_message(
            student_id,
            f"\U0001f614 Afsuski, {full_name}, arizangiz rad etildi.\n\n"
            f"Qo'shimcha ma'lumot uchun ustozga murojaat qiling."
        )
    except Exception as e:
        print(f"O'quvchiga xabar xatosi: {e}")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "<b>\U0001f4da Buyruqlar:</b>\n\n"
        "\U0001f4b0 /balance — bayt balansi\n"
        "\U0001f464 /profile — mening profilim\n"
        "\U0001f4dd /homework — uy vazifalarim\n\n"
        "Yoki pastdagi tugmani bosing \U0001f447",
        reply_markup=get_main_menu_keyboard()
    )


# ─────────────────────────────────────────────
# TEACHER PANEL — inline buttons handlers
# ─────────────────────────────────────────────

@router.callback_query(F.data == "teacher_students")
async def teacher_students_callback(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id != TEACHER_ID:
        await callback.answer("Bu faqat ustoz uchun!", show_alert=True)
        return

    students = await get_all_students()
    active = [s for s in students if s.get('is_active')]
    pending = [s for s in students if not s.get('is_active')]

    text = f"\U0001f465 <b>O'quvchilar ro'yxati</b>\n\n"
    text += f"\u2705 Faol: <b>{len(active)}</b> | \u23f3 Kutayotgan: <b>{len(pending)}</b>\n"
    text += "\u2500" * 20 + "\n\n"

    for i, s in enumerate(active[:20], 1):
        username = f"@{s['username']}" if s.get('username') else f"ID:{s['telegram_id']}"
        calf = s.get('calf_kg', 40) or 40
        text += f"<b>{i}.</b> {s['full_name']} | {username}\n"
        text += f"   \U0001f42e {calf} kg | \U0001f4be {s.get('bytes_balance', 0)} bayt\n"

    if len(active) > 20:
        text += f"\n... va yana {len(active) - 20} ta o'quvchi"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="\u2b05\ufe0f Orqaga", callback_data="teacher_back")
    ]])
    await callback.message.edit_text(text, reply_markup=back_kb)
    await callback.answer()


@router.callback_query(F.data == "teacher_broadcast")
async def teacher_broadcast_callback(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != TEACHER_ID:
        await callback.answer("Bu faqat ustoz uchun!", show_alert=True)
        return

    await state.set_state(BroadcastStates.waiting_message)
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
        text="\u274c Bekor qilish", callback_data="teacher_broadcast_cancel"
    )]])
    await callback.message.edit_text(
        "\U0001f4e2 <b>Barcha o'quvchilarga xabar</b>\n\n"
        "Yuboriladigan xabar matnini yozing:\n\n"
        "<i>Xabar emoji, bold yoki oddiy matn bo'lishi mumkin</i>",
        reply_markup=cancel_kb
    )
    await callback.answer()


@router.callback_query(F.data == "teacher_broadcast_cancel")
async def teacher_broadcast_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    teacher_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4cb  O'quvchilar ro'yxati", callback_data="teacher_students")],
        [InlineKeyboardButton(text="\U0001f4e2  Barcha o'quvchilarga xabar", callback_data="teacher_broadcast")],
    ])
    await callback.message.edit_text(
        "\U0001f44b Salom, <b>ustoz</b>!\n\n"
        "\U0001f3eb <b>A Avlod Academy</b> boshqaruv paneli\n\n"
        "Kerakli bo'limni tanlang \U0001f447",
        reply_markup=teacher_keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "teacher_back")
async def teacher_back_callback(callback: types.CallbackQuery):
    if callback.from_user.id != TEACHER_ID:
        await callback.answer()
        return
    teacher_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4cb  O'quvchilar ro'yxati", callback_data="teacher_students")],
        [InlineKeyboardButton(text="\U0001f4e2  Barcha o'quvchilarga xabar", callback_data="teacher_broadcast")],
    ])
    await callback.message.edit_text(
        "\U0001f44b Salom, <b>ustoz</b>!\n\n"
        "\U0001f3eb <b>A Avlod Academy</b> boshqaruv paneli\n\n"
        "Kerakli bo'limni tanlang \U0001f447",
        reply_markup=teacher_keyboard
    )
    await callback.answer()


@router.message(BroadcastStates.waiting_message)
async def process_broadcast_message(message: types.Message, bot: Bot, state: FSMContext):
    if message.from_user.id != TEACHER_ID:
        return

    msg_text = message.text or message.caption or ""
    if not msg_text:
        await message.answer("\u26a0\ufe0f Xabar matni bo'sh. Qayta yozing.")
        return

    students = await get_all_students()
    active = [s for s in students if s.get('is_active')]

    await message.answer(f"\u23f3 Yuborilmoqda... ({len(active)} ta o'quvchi)")

    sent = 0
    failed = 0
    for student in active:
        try:
            await bot.send_message(student['telegram_id'], msg_text)
            sent += 1
        except Exception:
            failed += 1

    await state.clear()

    teacher_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f4cb  O'quvchilar ro'yxati", callback_data="teacher_students")],
        [InlineKeyboardButton(text="\U0001f4e2  Barcha o'quvchilarga xabar", callback_data="teacher_broadcast")],
    ])
    await message.answer(
        f"\u2705 <b>Xabar yuborildi!</b>\n\n"
        f"\U0001f4e4 Yuborildi: <b>{sent}</b> ta\n"
        f"\u274c Xato: <b>{failed}</b> ta",
        reply_markup=teacher_keyboard
    )
