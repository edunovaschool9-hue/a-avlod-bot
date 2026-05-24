from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database import (
    get_all_students,
    add_bytes,
    find_student_by_username,
    activate_student,
    get_student_by_username,
    unlock_next_lesson,
    update_calf,
    add_som,
    update_student_name,
    approve_tez_aytish,
    reject_tez_aytish,
    activate_tez_aytish_for_student,
    set_student_schedule,
    delete_student_schedule,
    get_student_schedule,
    get_all_schedules,
)

from config import TEACHER_ID

router = Router()

DAYS_UZ = {
    0: "Dushanba",
    1: "Seshanba",
    2: "Chorshanba",
    3: "Payshanba",
    4: "Juma",
    5: "Shanba",
    6: "Yakshanba",
}

HOURS = ["09:00","10:00","11:00","12:00","13:00","14:00","15:00",
         "16:00","17:00","18:00","19:00","20:00","21:00"]

class RenameStudentStates(StatesGroup):
    waiting_new_name = State()

class ScheduleStates(StatesGroup):
    choosing_student = State()
    choosing_days = State()
    choosing_time = State()

def is_teacher(user_id):
    return user_id == TEACHER_ID

@router.message(Command("students"))
async def cmd_students(message: types.Message):
    if not is_teacher(message.from_user.id):
        await message.answer("Bu buyruq faqat ustoz uchun.")
        return

    students = await get_all_students()

    if not students:
        await message.answer("\U0001f4ed Hozircha o'quvchilar yo'q.")
        return

    text = "\U0001f465 <b>O'quvchilar ro'yxati</b>\n\n"
    active = [s for s in students if s.get('is_active')]
    pending = [s for s in students if not s.get('is_active')]

    if active:
        text += "\u2705 <b>Faol:</b>\n"
        for i, s in enumerate(active, 1):
            username = f"@{s['username']}" if s.get('username') else "username yo'q"
            status = "\u2705"
            text += (
                f"{i}. {status} <b>{s['full_name']}</b>\n"
                f" \U0001f464 {username}\n"
                f" \U0001f4be {s.get('bytes_balance', 0)} bayt | "
                f"\U0001f4b0 {s.get('som_balance', 0):,} so'm | "
                f"\U0001f42e {s.get('calf_kg', 0)} kg\n\n"
            )

    if pending:
        text += "\u23f3 <b>Kutayotgan:</b>\n"
        for i, s in enumerate(pending, 1):
            username = f"@{s['username']}" if s.get('username') else "username yo'q"
            text += f"{i}. \u23f3 <b>{s['full_name']}</b> ({username})\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="\u2795 O'quvchi qo'shish", callback_data="add_student_help"),
            InlineKeyboardButton(text="\U0001f5d1 O'quvchi o'chirish", callback_data="delete_student_help"),
        ],
        [
            InlineKeyboardButton(text="\u270f\ufe0f Ismni o'zgartirish", callback_data="rename_student_help"),
            InlineKeyboardButton(text="\U0001f504 Yangilash", callback_data="refresh_students"),
        ],
        [
            InlineKeyboardButton(text="\U0001f4c5 Dars jadvali", callback_data="schedule_help"),
        ]
    ])

    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data == "refresh_students")
async def refresh_students(callback: CallbackQuery):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    students = await get_all_students()
    active = [s for s in students if s.get('is_active')]
    pending = [s for s in students if not s.get('is_active')]

    text = "\U0001f465 <b>O'quvchilar ro'yxati</b>\n\n"
    if active:
        text += "\u2705 <b>Faol:</b>\n"
        for i, s in enumerate(active, 1):
            username = f"@{s['username']}" if s.get('username') else "username yo'q"
            text += (
                f"{i}. \u2705 <b>{s['full_name']}</b>\n"
                f" \U0001f464 {username}\n"
                f" \U0001f4be {s.get('bytes_balance', 0)} bayt | "
                f"\U0001f4b0 {s.get('som_balance', 0):,} so'm | "
                f"\U0001f42e {s.get('calf_kg', 0)} kg\n\n"
            )
    if pending:
        text += "\u23f3 <b>Kutayotgan:</b>\n"
        for i, s in enumerate(pending, 1):
            username = f"@{s['username']}" if s.get('username') else "username yo'q"
            text += f"{i}. \u23f3 <b>{s['full_name']}</b> ({username})\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="\u2795 O'quvchi qo'shish", callback_data="add_student_help"),
            InlineKeyboardButton(text="\U0001f5d1 O'quvchi o'chirish", callback_data="delete_student_help"),
        ],
        [
            InlineKeyboardButton(text="\u270f\ufe0f Ismni o'zgartirish", callback_data="rename_student_help"),
            InlineKeyboardButton(text="\U0001f504 Yangilash", callback_data="refresh_students"),
        ],
        [
            InlineKeyboardButton(text="\U0001f4c5 Dars jadvali", callback_data="schedule_help"),
        ]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("\u2705 Yangilandi!")

@router.callback_query(F.data == "add_student_help")
async def add_student_help(callback: CallbackQuery):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    text = (
        "\u2795 <b>O'quvchi qo'shish:</b>\n\n"
        "Quyidagi formatda yozing:\n\n"
        "<code>/add_student @username 500000</code>\n\n"
        "\U0001f4cc username — o'quvchining Telegram username\n"
        "\U0001f4b0 500000 — kurs narxi (so'm)\n\n"
        "\u26a0\ufe0f O'quvchi avval /start bosgan bo'lishi kerak!"
    )
    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "delete_student_help")
async def delete_student_help(callback: CallbackQuery):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    students = await get_all_students()

    if not students:
        await callback.message.answer("\U0001f4ed O'chirish uchun o'quvchilar yo'q.")
        await callback.answer()
        return

    text = "\U0001f5d1 <b>Qaysi o'quvchini o'chirmoqchisiz?</b>"

    buttons = []
    for s in students[:10]:
        username = s.get('username') or 'nousername'
        buttons.append([InlineKeyboardButton(
            text=f"\U0001f5d1 {s['full_name']} (@{username})",
            callback_data=f"del_student_{s['telegram_id']}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("del_student_"))
async def del_student_confirm(callback: CallbackQuery, bot: Bot):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    telegram_id = int(callback.data.split("_")[2])

    from database import get_student
    student = await get_student(telegram_id)
    if not student:
        await callback.answer("O'quvchi topilmadi!")
        return

    name = student['full_name']
    username = student.get('username') or 'nousername'

    pool = await __import__('database', fromlist=['get_pool']).get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM students WHERE telegram_id = $1", telegram_id)

    await callback.message.edit_text(
        f"\u2705 <b>O'quvchi o'chirildi!</b>\n\n"
        f"\U0001f464 {name} (@{username})"
    )

    try:
        await bot.send_message(
            telegram_id,
            "\u274c Sizning hisobingiz o'chirildi.\n"
            "Batafsil ma'lumot uchun ustoz bilan bog'laning."
        )
    except Exception:
        pass

    await callback.answer("\u2705 O'chirildi!")

@router.callback_query(F.data == "rename_student_help")
async def rename_student_help(callback: CallbackQuery):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    students = await get_all_students()

    if not students:
        await callback.message.answer("\U0001f4ed O'quvchilar yo'q.")
        await callback.answer()
        return

    text = "\u270f\ufe0f <b>Qaysi o'quvchining ismini o'zgartirasiz?</b>"

    buttons = []
    for s in students[:10]:
        username = s.get('username') or 'nousername'
        buttons.append([InlineKeyboardButton(
            text=f"\u270f\ufe0f {s['full_name']} (@{username})",
            callback_data=f"rename_std_{s['telegram_id']}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("rename_std_"))
async def rename_std_select(callback: CallbackQuery, state: FSMContext):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    telegram_id = int(callback.data.split("_")[2])
    await state.set_state(RenameStudentStates.waiting_new_name)
    await state.update_data(target_id=telegram_id)
    await callback.message.answer(
        "\u270f\ufe0f Yangi ismni yozing:"
    )
    await callback.answer()

@router.message(RenameStudentStates.waiting_new_name)
async def rename_std_done(message: types.Message, state: FSMContext):
    if not is_teacher(message.from_user.id):
        await state.clear()
        return

    data = await state.get_data()
    target_id = data.get('target_id')
    new_name = message.text.strip()

    await update_student_name(target_id, new_name)
    await state.clear()
    await message.answer(f"\u2705 Ism o'zgartirildi: <b>{new_name}</b>")

# ─────────────────────────────────────────────
# SCHEDULE (JADVAL) HANDLERS
# ─────────────────────────────────────────────

@router.callback_query(F.data == "schedule_help")
async def schedule_help(callback: CallbackQuery, state: FSMContext):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    students = await get_all_students()
    active = [s for s in students if s.get('is_active')]

    if not active:
        await callback.message.answer("\U0001f4ed Faol o'quvchilar yo'q.")
        await callback.answer()
        return

    text = "\U0001f4c5 <b>Dars jadvali</b>\nQaysi o'quvchiga jadval belgilaysiz?"

    buttons = []
    for s in active[:15]:
        username = s.get('username') or 'nousername'
        buttons.append([InlineKeyboardButton(
            text=f"\U0001f464 {s['full_name']} (@{username})",
            callback_data=f"sched_student_{s['telegram_id']}"
        )])
    buttons.append([InlineKeyboardButton(text="\U0001f4cb Barcha jadvallar", callback_data="sched_view_all")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "sched_view_all")
async def sched_view_all(callback: CallbackQuery):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    schedules = await get_all_schedules()
    if not schedules:
        await callback.message.answer("\U0001f4c5 Jadvallar yo'q.")
        await callback.answer()
        return

    text = "\U0001f4c5 <b>Barcha dars jadvallari:</b>\n\n"
    by_student = {}
    for sc in schedules:
        sid = sc['student_id']
        if sid not in by_student:
            by_student[sid] = {'name': sc['full_name'], 'username': sc.get('username',''), 'days': []}
        day_name = DAYS_UZ.get(sc['day_of_week'], str(sc['day_of_week']))
        by_student[sid]['days'].append(f"{day_name} {sc['lesson_time']}")

    for sid, info in by_student.items():
        text += f"\U0001f464 <b>{info['name']}</b>"
        if info['username']:
            text += f" (@{info['username']})"
        text += "\n"
        for day in info['days']:
            text += f"  \U0001f4cc {day}\n"
        text += "\n"

    await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data.startswith("sched_student_"))
async def sched_student_select(callback: CallbackQuery, state: FSMContext):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    student_id = int(callback.data.split("_")[2])

    from database import get_student
    student = await get_student(student_id)
    if not student:
        await callback.answer("O'quvchi topilmadi!")
        return

    # Show current schedule
    current = await get_student_schedule(student_id)
    current_days = {sc['day_of_week'] for sc in current}

    await state.set_state(ScheduleStates.choosing_days)
    await state.update_data(
        sched_student_id=student_id,
        sched_student_name=student['full_name'],
        selected_days=[],
        current_days=list(current_days)
    )

    text = (
        f"\U0001f4c5 <b>{student['full_name']}</b> uchun dars kunlarini tanlang\n\n"
        f"Hozirgi jadval: {', '.join([DAYS_UZ[d] for d in sorted(current_days)]) if current_days else 'belgilanmagan'}\n\n"
        "Yangi kunlarni belgilang (2 ta kun tavsiya etiladi):"
    )

    buttons = []
    for day_num, day_name in DAYS_UZ.items():
        is_current = day_num in current_days
        mark = "\u2705 " if is_current else ""
        buttons.append([InlineKeyboardButton(
            text=f"{mark}{day_name}",
            callback_data=f"sched_day_{day_num}"
        )])
    buttons.append([InlineKeyboardButton(text="\u274c Bekor qilish", callback_data="sched_cancel")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("sched_day_"), ScheduleStates.choosing_days)
async def sched_day_select(callback: CallbackQuery, state: FSMContext):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    day_num = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected_days = data.get('selected_days', [])

    if day_num in selected_days:
        selected_days.remove(day_num)
    else:
        selected_days.append(day_num)

    await state.update_data(selected_days=selected_days)

    selected_names = [DAYS_UZ[d] for d in sorted(selected_days)]
    student_name = data.get('sched_student_name', '')
    current_days = set(data.get('current_days', []))

    text = (
        f"\U0001f4c5 <b>{student_name}</b> uchun dars kunlari\n\n"
        f"Tanlangan: <b>{', '.join(selected_names) if selected_names else 'hech narsa'}</b>\n\n"
        "Yana kun tanlang yoki davom eting:"
    )

    buttons = []
    for day_num2, day_name in DAYS_UZ.items():
        is_selected = day_num2 in selected_days
        is_current = day_num2 in current_days
        mark = "\u2705 " if is_selected else ("\U0001f4cc " if is_current else "")
        buttons.append([InlineKeyboardButton(
            text=f"{mark}{day_name}",
            callback_data=f"sched_day_{day_num2}"
        )])

    if selected_days:
        buttons.append([InlineKeyboardButton(
            text=f"\u27a1\ufe0f Davom etish ({len(selected_days)} kun)",
            callback_data="sched_days_done"
        )])
    buttons.append([InlineKeyboardButton(text="\u274c Bekor qilish", callback_data="sched_cancel")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data == "sched_days_done", ScheduleStates.choosing_days)
async def sched_days_done(callback: CallbackQuery, state: FSMContext):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    data = await state.get_data()
    selected_days = data.get('selected_days', [])

    if not selected_days:
        await callback.answer("Kamida 1 kun tanlang!", show_alert=True)
        return

    await state.set_state(ScheduleStates.choosing_time)
    await state.update_data(current_day_index=0)

    current_day = selected_days[0]
    day_name = DAYS_UZ[current_day]
    student_name = data.get('sched_student_name', '')

    text = f"\U0001f4c5 <b>{student_name}</b>\n{day_name} uchun dars vaqtini tanlang:"

    buttons = []
    for h in HOURS:
        buttons.append([InlineKeyboardButton(text=f"\U0001f554 {h}", callback_data=f"sched_time_{h}")])
    buttons.append([InlineKeyboardButton(text="\u274c Bekor qilish", callback_data="sched_cancel")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(F.data.startswith("sched_time_"), ScheduleStates.choosing_time)
async def sched_time_select(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    time_val = callback.data.replace("sched_time_", "")
    data = await state.get_data()
    selected_days = data.get('selected_days', [])
    current_idx = data.get('current_day_index', 0)
    student_id = data.get('sched_student_id')
    student_name = data.get('sched_student_name', '')

    current_day = selected_days[current_idx]
    day_name = DAYS_UZ[current_day]

    # Save this day's schedule
    await set_student_schedule(student_id, current_day, time_val)

    # Check if there are more days to set
    next_idx = current_idx + 1
    if next_idx < len(selected_days):
        await state.update_data(current_day_index=next_idx)
        next_day = selected_days[next_idx]
        next_day_name = DAYS_UZ[next_day]

        text = (
            f"\u2705 {day_name}: <b>{time_val}</b> saqlandi!\n\n"
            f"\U0001f4c5 <b>{student_name}</b>\n"
            f"{next_day_name} uchun dars vaqtini tanlang:"
        )

        buttons = []
        for h in HOURS:
            buttons.append([InlineKeyboardButton(text=f"\U0001f554 {h}", callback_data=f"sched_time_{h}")])
        buttons.append([InlineKeyboardButton(text="\u274c Bekor qilish", callback_data="sched_cancel")])

        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        await callback.answer(f"\u2705 {day_name} {time_val} saqlandi!")
    else:
        # All days done
        await state.clear()

        # Get full schedule
        schedule = await get_student_schedule(student_id)
        schedule_text = ""
        for sc in sorted(schedule, key=lambda x: x['day_of_week']):
            d = DAYS_UZ.get(sc['day_of_week'], str(sc['day_of_week']))
            schedule_text += f"  \U0001f4cc {d}: {sc['lesson_time']}\n"

        result_text = (
            f"\u2705 <b>Jadval belgilandi!</b>\n\n"
            f"\U0001f464 {student_name}\n\n"
            f"<b>Jadval:</b>\n{schedule_text}\n"
            f"O'quvchiga dars kunidan 1 kun oldin eslatma yuboriladi!"
        )

        await callback.message.edit_text(result_text)
        await callback.answer("\u2705 Jadval saqlandi!")

        # Notify student
        try:
            await bot.send_message(
                student_id,
                f"\U0001f4c5 <b>Dars jadvalingiz belgilandi!</b>\n\n"
                f"<b>Jadvalingiz:</b>\n{schedule_text}\n"
                f"\U0001f514 Har bir dars kunidan 1 kun oldin eslatma olasiz!"
            )
        except Exception:
            pass

@router.callback_query(F.data == "sched_cancel")
async def sched_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("\u274c Bekor qilindi.")
    await callback.answer()

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
    await activate_tez_aytish_for_student(student['telegram_id'])

    await message.answer(
        f"\u2705 <b>O'quvchi qo'shildi!</b>\n\n"
        f"\U0001f464 {student['full_name']} (@{username})\n"
        f"\U0001f4b0 To'lov: {som_amount:,} so'm\n\n"
        f"Tez aytish va darslar aktivlashtirildi!"
    )

    try:
        await bot.send_message(
            student['telegram_id'],
            "\U0001f389 <b>Siz A Avlod Akademiyasiga qabul qilindingiz!</b>\n\n"
            "\U0001f4da /darslar — Darslarga kirish\n"
            "\U0001f464 /profile — Profilingiz\n\n"
            "Muvaffaqiyatlar! \U0001f680"
        )
    except Exception:
        pass

@router.message(Command("approve_test"))
async def cmd_approve_test(message: types.Message, bot: Bot):
    if not is_teacher(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("<code>/approve_test @username lesson_id</code>")
        return

    username = parts[1].lstrip('@')
    try:
        lesson_id = int(parts[2])
    except ValueError:
        await message.answer("lesson_id son bo'lishi kerak.")
        return

    student = await get_student_by_username(username)
    if not student:
        await message.answer(f"@{username} topilmadi.")
        return

    bytes_earned = 25
    await add_bytes(student['telegram_id'], bytes_earned, f"{lesson_id}-dars testi")
    await update_calf(student['telegram_id'], 1.0)
    await unlock_next_lesson(student['telegram_id'], lesson_id)

    await message.answer(
        f"\u2705 Tasdiqlandi!\n"
        f"\U0001f464 {student['full_name']}\n"
        f"\U0001f4da {lesson_id}-dars\n"
        f"+{bytes_earned} bayt, +1 kg\n"
        f"{lesson_id + 1}-dars testi ochildi"
    )

    try:
        await bot.send_message(
            student['telegram_id'],
            f"\U0001f389 <b>Test tasdiqlandi!</b>\n\n"
            f"\U0001f4da {lesson_id}-dars testi\n"
            f"\U0001f4be <b>+{bytes_earned} bayt</b>\n"
            f"\U0001f42e Buzoqcha <b>+1 kg</b> oldi!\n\n"
            f"\U0001f4d6 {lesson_id + 1}-dars testi endi ochiq!\n"
            f"Akademiyani oching! \U0001f680"
        )
    except Exception:
        pass

@router.message(Command("warn"))
async def cmd_warn(message: types.Message, bot: Bot):
    if not is_teacher(message.from_user.id):
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 2:
        await message.answer("<code>/warn @username sabab</code>")
        return

    username = parts[1].lstrip('@')
    reason = parts[2] if len(parts) > 2 else "Vazifa bajarilmadi"

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

    await update_calf(student['telegram_id'], -kg_penalty)

    if som_penalty:
        await add_som(student['telegram_id'], -som_penalty, f"Jarima: {reason}")

    from database import add_warning
    await add_warning(student['telegram_id'])

    penalty_text = (
        f"\U0001f4b0 -{som_penalty:,} so'm jarima"
        if som_penalty
        else ""
    )

    await message.answer(
        f"\u26a0\ufe0f Ogohlantirish #{warnings}\n"
        f"\U0001f464 {student['full_name']}\n"
        f"\U0001f42e -{kg_penalty} kg\n"
        f"{penalty_text}"
    )

    try:
        msg = (
            f"\u26a0\ufe0f <b>Ogohlantirish #{warnings}!</b>\n\n"
            f"Sabab: {reason}\n"
            f"\U0001f42e Buzoqchadan <b>-{kg_penalty} kg</b> ayirildi"
        )
        if som_penalty:
            msg += f"\n\U0001f4b0 <b>-{som_penalty:,} so'm</b> jarima"
        await bot.send_message(student['telegram_id'], msg)
    except Exception:
        pass

@router.message(Command("add_bytes"))
async def cmd_add_bytes(message: types.Message, bot: Bot):
    if not is_teacher(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("<code>/add_bytes @username amount</code>")
        return

    username = parts[1].lstrip('@')
    try:
        amount = int(parts[2])
    except ValueError:
        await message.answer("Miqdor son bo'lishi kerak.")
        return

    student = await get_student_by_username(username)
    if not student:
        await message.answer(f"@{username} topilmadi.")
        return

    await add_bytes(student['telegram_id'], amount, "Ustoz tomonidan qo'shildi")
    await message.answer(f"\u2705 {student['full_name']}ga +{amount} bayt qo'shildi!")

    try:
        await bot.send_message(
            student['telegram_id'],
            f"\U0001f4be <b>+{amount} bayt!</b>\n\nUstoz tomonidan qo'shildi!"
        )
    except Exception:
        pass

@router.message(Command("sub_bytes"))
async def cmd_sub_bytes(message: types.Message, bot: Bot):
    if not is_teacher(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("<code>/sub_bytes @username amount</code>")
        return

    username = parts[1].lstrip('@')
    try:
        amount = int(parts[2])
    except ValueError:
        await message.answer("Miqdor son bo'lishi kerak.")
        return

    student = await get_student_by_username(username)
    if not student:
        await message.answer(f"@{username} topilmadi.")
        return

    await add_bytes(student['telegram_id'], -amount, "Ustoz tomonidan ayirildi")
    await message.answer(f"\u2705 {student['full_name']}dan -{amount} bayt ayirildi!")

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if not is_teacher(message.from_user.id):
        return

    students = await get_all_students()
    active = [s for s in students if s.get('is_active')]
    pending = [s for s in students if not s.get('is_active')]

    total_bytes = sum(s.get('bytes_balance', 0) for s in active)
    total_som = sum(s.get('som_balance', 0) for s in active)
    avg_calf = sum(s.get('calf_kg', 0) for s in active) / len(active) if active else 0

    await message.answer(
        f"\U0001f4ca <b>Statistika</b>\n\n"
        f"\U0001f465 Jami o'quvchilar: <b>{len(students)}</b>\n"
        f"\u2705 Faol: <b>{len(active)}</b>\n"
        f"\u23f3 Kutayotgan: <b>{len(pending)}</b>\n\n"
        f"\U0001f4be Jami baytlar: <b>{total_bytes}</b>\n"
        f"\U0001f4b0 Jami hisob: <b>{total_som:,} so'm</b>\n"
        f"\U0001f42e O'rtacha buzoqcha: <b>{avg_calf:.1f} kg</b>"
    )

@router.callback_query(F.data.startswith("taz_ok_"))
async def taz_approve(callback: CallbackQuery, bot: Bot):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    submission_id = int(parts[2])
    student_id = int(parts[3])
    lesson_id = int(parts[4])

    await approve_tez_aytish(submission_id, student_id, lesson_id)

    from lessons_data import TEZ_AYTISH_LESSONS
    lesson = next((l for l in TEZ_AYTISH_LESSONS if l["id"] == lesson_id), None)
    next_lesson = next((l for l in TEZ_AYTISH_LESSONS if l["id"] == lesson_id + 1), None)

    await callback.message.edit_caption(
        callback.message.caption + "\n\n\u2705 <b>TASDIQLANDI!</b>"
    )
    await callback.answer("\u2705 Tasdiqlandi!")

    try:
        if next_lesson:
            await bot.send_message(
                student_id,
                f"\U0001f389 <b>Tez aytish tasdiqlandi!</b>\n\n"
                f"\u2705 {lesson_id}-dars: <b>{lesson['title'] if lesson else ''}</b>\n\n"
                f"\U0001f513 Keyingi dars ochildi!\n"
                f"\U0001f4da {lesson_id + 1}-dars: <b>{next_lesson['title']}</b>\n\n"
                f"Davom eting! \U0001f680"
            )
        else:
            await bot.send_message(
                student_id,
                f"\U0001f38a <b>Barakalla! Barcha tez aytishlarni tugatdingiz!</b>\n\n"
                f"\u2705 {lesson_id}-dars tasdiqlandi!\n"
                f"Siz 1 oylik tez aytish kursini muvaffaqiyatli tugatdingiz! \U0001f38a"
            )
    except Exception:
        pass

@router.callback_query(F.data.startswith("taz_no_"))
async def taz_reject(callback: CallbackQuery, bot: Bot):
    if not is_teacher(callback.from_user.id):
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    submission_id = int(parts[2])
    student_id = int(parts[3])
    lesson_id = int(parts[4])

    await reject_tez_aytish(submission_id, student_id, lesson_id)

    from lessons_data import TEZ_AYTISH_LESSONS
    lesson = next((l for l in TEZ_AYTISH_LESSONS if l["id"] == lesson_id), None)

    await callback.message.edit_caption(
        callback.message.caption + "\n\n\u274c <b>RAD ETILDI — qayta yozadi</b>"
    )
    await callback.answer("\u274c Rad etildi!")

    try:
        await bot.send_message(
            student_id,
            f"\u274c <b>Tez aytish rad etildi</b>\n\n"
            f"\U0001f4da {lesson_id}-dars: {lesson['title'] if lesson else ''}\n\n"
            f"Qayta yozib yuboring! \U0001f3a4"
        )
    except Exception:
        pass


# ─────────────────────────────────────────────
# ANNOUNCE — broadcast message to all active students
# ─────────────────────────────────────────────

@router.message(Command("announce"))
async def cmd_announce(message: types.Message, bot: Bot):
    if not is_teacher(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "\u26a0\ufe0f Format:\n<code>/announce Xabar matni</code>\n\n"
            "Barcha faol o'quvchilarga xabar yuboriladi."
        )
        return

    msg_text = parts[1]
    students = await get_all_students()
    active = [s for s in students if s.get('is_active')]

    if not active:
        await message.answer("\u26a0\ufe0f Faol o'quvchilar topilmadi.")
        return

    sent = 0
    failed = 0
    for student in active:
        try:
            await bot.send_message(
                student['telegram_id'],
                msg_text
            )
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"\u2705 <b>Xabar yuborildi!</b>\n\n"
        f"\U0001f4e4 Yuborildi: <b>{sent}</b>\n"
        f"\u274c Xato: <b>{failed}</b>"
    )
