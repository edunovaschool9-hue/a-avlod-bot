from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import find_student_by_username, create_homework, get_student_homeworks, submit_homework
from config import TEACHER_ID

router = Router()


class NewHomeworkStates(StatesGroup):
    waiting_username = State()
    waiting_title = State()
    waiting_description = State()
    waiting_reward = State()


@router.message(Command("new_hw"))
async def cmd_new_homework(message: types.Message, state: FSMContext):
    if message.from_user.id != TEACHER_ID:
        await message.answer("Bu buyruq faqat ustoz uchun.")
        return
    await message.answer(
        "📝 <b>Yangi uy vazifasi</b>\n\n"
        "1/4-qadam: Qaysi o'quvchiga?\n"
        "O'quvchining @username ini yozing.\n\n"
        "<i>Bekor qilish: /cancel</i>"
    )
    await state.set_state(NewHomeworkStates.waiting_username)


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    current = await state.get_state()
    if current:
        await state.clear()
        await message.answer("Bekor qilindi.")


@router.message(NewHomeworkStates.waiting_username)
async def process_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    student = await find_student_by_username(username)
    if not student:
        await message.answer(f"{username} topilmadi. Qayta urining yoki /cancel")
        return
    await state.update_data(student_id=student['telegram_id'], student_name=student['full_name'])
    await message.answer(
        f"✅ O'quvchi: <b>{student['full_name']}</b>\n\n"
        f"2/4-qadam: Vazifa nomi?\n"
        f"<i>Masalan: Rils stsenariysi yozish</i>"
    )
    await state.set_state(NewHomeworkStates.waiting_title)


@router.message(NewHomeworkStates.waiting_title)
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer(
        "3/4-qadam: Vazifa tavsifi?\n"
        "<i>Nima qilish kerak. Tavsif yoq bolsa - yozing.</i>"
    )
    await state.set_state(NewHomeworkStates.waiting_description)


@router.message(NewHomeworkStates.waiting_description)
async def process_description(message: types.Message, state: FSMContext):
    description = message.text if message.text != "-" else ""
    await state.update_data(description=description)
    await message.answer(
        "4/4-qadam: Necha bayt mukofot?\n"
        "<i>Masalan: 50</i>"
    )
    await state.set_state(NewHomeworkStates.waiting_reward)


@router.message(NewHomeworkStates.waiting_reward)
async def process_reward(message: types.Message, state: FSMContext, bot: Bot):
    try:
        reward = int(message.text)
    except ValueError:
        await message.answer("Son kiriting. Qayta urining.")
        return
    if reward < 0:
        await message.answer("Mukofot manfiy bolamaydi.")
        return
    data = await state.get_data()
    hw_id = await create_homework(
        student_id=data['student_id'],
        title=data['title'],
        description=data['description'],
        reward_bytes=reward
    )
    await message.answer(
        f"✅ <b>Vazifa yaratildi!</b>\n\n"
        f"👤 O'quvchi: {data['student_name']}\n"
        f"📝 Vazifa: {data['title']}\n"
        f"💾 Mukofot: {reward} bayt\n"
        f"ID: #{hw_id}"
    )
    try:
        text = f"🆕 <b>Yangi uy vazifasi!</b>\n\n📝 <b>{data['title']}</b>\n"
        if data['description']:
            text += f"\n{data['description']}\n"
        text += f"\n💾 Mukofot: <b>{reward} bayt</b>\n\nBajarib bo'lgach daftar rasmini yuboring."
        await bot.send_message(data['student_id'], text)
    except Exception:
        pass
    await state.clear()


@router.message(F.photo)
async def handle_photo(message: types.Message, bot: Bot):
    if message.from_user.id == TEACHER_ID:
        return
    homeworks = await get_student_homeworks(message.from_user.id, status='new')
    if not homeworks:
        await message.answer("Faol vazifangiz yoq. /homework buyrug'ini ko'ring.")
        return
    hw = homeworks[0]
    photo_id = message.photo[-1].file_id
    await submit_homework(hw['id'], photo_id)
    await message.answer(
        f"✅ Rasm qabul qilindi!\n\n"
        f"📝 Vazifa: <b>{hw['title']}</b>\n"
        f"🔍 Holat: tekshirilmoqda\n\n"
        f"Ustoz tekshirib bayt qoshadi 💾"
    )
    try:
        username = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
        await bot.send_photo(
            TEACHER_ID,
            photo=photo_id,
            caption=(
                f"📥 <b>Yangi vazifa topshirildi</b>\n\n"
                f"👤 Kim: {message.from_user.full_name} ({username})\n"
                f"📝 Vazifa: <b>{hw['title']}</b>\n"
                f"💾 Mukofot: {hw['reward_bytes']} bayt\n\n"
                f"<code>/add_bytes {username} {hw['reward_bytes']} Vazifa #{hw['id']}</code>"
            )
        )
    except Exception:
        pass
