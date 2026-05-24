from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import (
    get_student, add_bytes, get_lesson_access, unlock_next_lesson, update_calf,
    get_tez_aytish_access, submit_tez_aytish_voice, get_pending_tez_aytish
)
from config import TEACHER_ID
from lessons_data import MONTHLY_LESSONS, TEZ_AYTISH_LESSONS

router = Router()


class TestStates(StatesGroup):
    answering = State()

class TezAytishStates(StatesGroup):
    waiting_voice = State()


def get_lesson(lesson_id: int):
    for lesson in MONTHLY_LESSONS:
        if lesson["id"] == lesson_id:
            return lesson
    return None


def get_tez_lesson(lesson_id: int):
    for lesson in TEZ_AYTISH_LESSONS:
        if lesson["id"] == lesson_id:
            return lesson
    return None


def lesson_keyboard(unlocked_ids=None):
    """Build lessons keyboard. unlocked_ids - set of accessible lesson IDs."""
    builder = InlineKeyboardBuilder()
    for lesson in MONTHLY_LESSONS:
        lid = lesson["id"]
        if unlocked_ids is None or lid in unlocked_ids:
            builder.button(
                text=f"\U0001f4da {lid}-dars: {lesson['title']}",
                callback_data=f"lesson_{lid}"
            )
        else:
            builder.button(
                text=f"\U0001f512 {lid}-dars: {lesson['title']}",
                callback_data="lesson_locked"
            )
    builder.adjust(1)
    return builder.as_markup()


def tez_aytish_keyboard(access_list):
    """Build tez aytish keyboard from access list."""
    builder = InlineKeyboardBuilder()
    for acc in access_list:
        lid = acc['lesson_id']
        status = acc.get('status', 'locked')
        lesson = get_tez_lesson(lid)
        title = lesson['title'] if lesson else f"{lid}-dars"

        if status == 'open':
            icon = "\U0001f3a4"
        elif status == 'pending':
            icon = "\u23f3"
        elif status == 'done':
            icon = "\u2705"
        else:
            icon = "\U0001f512"

        builder.button(
            text=f"{icon} {lid}-dars: {title}",
            callback_data=f"tez_{lid}" if status == 'open' else f"tez_view_{lid}"
        )
    builder.adjust(1)
    return builder.as_markup()


def lesson_blocks_keyboard(lesson_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="\U0001f9ea Test boshlash (+25 bayt)", callback_data=f"test_{lesson_id}_0")
    builder.button(text="\U0001f3ac Video darslik (tez orada)", callback_data="coming_soon")
    builder.button(text="\u21a9\ufe0f Darslarga qaytish", callback_data="back_lessons")
    builder.adjust(1)
    return builder.as_markup()


def answer_keyboard(lesson_id: int, question_idx: int, options: list):
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(options):
        builder.button(
            text=option,
            callback_data=f"answer_{lesson_id}_{question_idx}_{i}"
        )
    builder.adjust(1)
    return builder.as_markup()


@router.message(Command("darslar"))
async def cmd_lessons(message: types.Message):
    student = await get_student(message.from_user.id)
    if not student or not student.get('is_active'):
        await message.answer(
            "\u26a0\ufe0f Sizda darslar ochilmagan.\n"
            "Ustoz bilan bog'laning!"
        )
        return

    access = await get_lesson_access(message.from_user.id)
    unlocked_ids = {a['lesson_id'] for a in access}

    text = (
        "\U0001f4da <b>1 Oylik Darslar Rejasi</b>\n\n"
        "Haftada 2 marta dars — 4 hafta, 8 ta dars!\n"
        "Har bir darsda test yechib <b>25 bayt</b> ishlang!\n\n"
        "Qaysi darsni ochmoqchisiz?"
    )
    await message.answer(text, reply_markup=lesson_keyboard(unlocked_ids))


@router.callback_query(F.data == "back_lessons")
async def back_to_lessons(callback: types.CallbackQuery):
    access = await get_lesson_access(callback.from_user.id)
    unlocked_ids = {a['lesson_id'] for a in access}
    text = (
        "\U0001f4da <b>1 Oylik Darslar Rejasi</b>\n\n"
        "Haftada 2 marta dars — 4 hafta, 8 ta dars!\n"
        "Har bir darsda test yechib <b>25 bayt</b> ishlang!\n\n"
        "Qaysi darsni ochmoqchisiz?"
    )
    await callback.message.edit_text(text, reply_markup=lesson_keyboard(unlocked_ids))


@router.callback_query(F.data == "lesson_locked")
async def lesson_locked(callback: types.CallbackQuery):
    await callback.answer("\U0001f512 Bu dars hali ochilmagan! Avvalgi darsni bajaring.", show_alert=True)


@router.callback_query(F.data == "coming_soon")
async def coming_soon(callback: types.CallbackQuery):
    await callback.answer("\u23f3 Bu bo'lim tez orada ochiladi!", show_alert=True)


@router.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: types.CallbackQuery):
    lesson_id = int(callback.data.split("_")[1])

    # Check access
    access = await get_lesson_access(callback.from_user.id)
    unlocked_ids = {a['lesson_id'] for a in access}
    if lesson_id not in unlocked_ids:
        await callback.answer("\U0001f512 Bu dars hali ochilmagan!", show_alert=True)
        return

    lesson = get_lesson(lesson_id)
    if not lesson:
        await callback.answer("Dars topilmadi!")
        return

    # Check if test already passed
    acc = next((a for a in access if a['lesson_id'] == lesson_id), None)
    test_done = acc and acc.get('test_passed')
    test_status = "\u2705 Test bajarilgan" if test_done else "\U0001f9ea Test — 5 savol = <b>25 bayt</b>"

    text = (
        f"\U0001f4da <b>{lesson['id']}-dars: {lesson['title']}</b>\n"
        f"\U0001f4c5 {lesson['week']}-hafta\n\n"
        f"{lesson['description']}\n\n"
        f"{test_status}\n"
        f"\U0001f3ac Video darslik — <i>tez orada</i>"
    )
    await callback.message.edit_text(text, reply_markup=lesson_blocks_keyboard(lesson_id))


@router.callback_query(F.data.startswith("test_"))
async def start_test(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    lesson_id = int(parts[1])
    question_idx = int(parts[2])
    lesson = get_lesson(lesson_id)
    if not lesson:
        await callback.answer("Dars topilmadi!")
        return
    question = lesson["tests"][question_idx]
    total = len(lesson["tests"])
    await state.set_state(TestStates.answering)
    await state.update_data(lesson_id=lesson_id, question_idx=question_idx, score=0)
    text = (
        f"\U0001f9ea <b>{lesson['title']}</b>\n"
        f"Savol {question_idx + 1}/{total}\n\n"
        f"<b>{question['question']}</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=answer_keyboard(lesson_id, question_idx, question["options"])
    )


@router.callback_query(F.data.startswith("answer_"))
async def process_answer(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    parts = callback.data.split("_")
    lesson_id = int(parts[1])
    question_idx = int(parts[2])
    selected = int(parts[3])
    lesson = get_lesson(lesson_id)
    if not lesson:
        await callback.answer("Xatolik!")
        return
    question = lesson["tests"][question_idx]
    correct = question["correct"]
    total = len(lesson["tests"])
    data = await state.get_data()
    score = data.get("score", 0)
    if selected == correct:
        score += 1
        feedback = "\u2705 To'g'ri!"
    else:
        correct_text = question["options"][correct]
        feedback = f"\u274c Noto'g'ri! To'g'ri: <b>{correct_text}</b>"
    next_idx = question_idx + 1
    if next_idx < total:
        await state.update_data(score=score, question_idx=next_idx)
        next_question = lesson["tests"][next_idx]
        text = (
            f"\U0001f9ea <b>{lesson['title']}</b>\n"
            f"Savol {next_idx + 1}/{total}\n\n"
            f"{feedback}\n\n"
            f"<b>{next_question['question']}</b>"
        )
        await callback.message.edit_text(
            text,
            reply_markup=answer_keyboard(lesson_id, next_idx, next_question["options"])
        )
        await callback.answer(feedback)
    else:
        # Test finished
        await state.clear()
        bytes_earned = score * 5
        student = await get_student(callback.from_user.id)
        student_name = student['full_name'] if student else callback.from_user.full_name
        username = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
        if score == total:
            emoji = "\U0001f3c6 Mukammal!"
        elif score >= total * 0.8:
            emoji = "\u2b50 A'lo!"
        elif score >= total * 0.6:
            emoji = "\U0001f44d Yaxshi!"
        else:
            emoji = "\U0001f4aa Davom eting!"

        await callback.message.edit_text(
            f"\U0001f389 <b>Test yakunlandi!</b>\n\n"
            f"{emoji}\n\n"
            f"\U0001f4ca Natija: <b>{score}/{total}</b>\n"
            f"\U0001f4be Kutilayotgan bayt: <b>+{bytes_earned}</b>\n\n"
            f"\u23f3 O'qituvchi tekshirmoqda..."
        )

        # Send to teacher
        from aiogram.utils.keyboard import InlineKeyboardBuilder as IKB
        builder = IKB()
        builder.button(
            text=f"\u2705 Tasdiqlash (+{bytes_earned} bayt)",
            callback_data=f"tapprove_{callback.from_user.id}_{lesson_id}_{bytes_earned}_{score}_{total}"
        )
        builder.button(
            text="\u274c Rad etish",
            callback_data=f"treject_{callback.from_user.id}_{lesson_id}"
        )
        builder.adjust(1)

        try:
            await bot.send_message(
                TEACHER_ID,
                f"\U0001f9ea <b>Test natijasi</b>\n\n"
                f"\U0001f464 {student_name} ({username})\n"
                f"\U0001f4da {lesson_id}-dars: {lesson['title']}\n"
                f"\U0001f4ca Natija: <b>{score}/{total}</b> — {emoji}\n"
                f"\U0001f4be Mukofot: <b>+{bytes_earned} bayt</b>",
                reply_markup=builder.as_markup()
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("tapprove_"))
async def tap_approve(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id != TEACHER_ID:
        await callback.answer("Bu tugma faqat ustoz uchun!")
        return
    parts = callback.data.split("_")
    student_id = int(parts[1])
    lesson_id = int(parts[2])
    bytes_earned = int(parts[3])
    score = int(parts[4])
    total = int(parts[5])
    lesson = get_lesson(lesson_id)

    await add_bytes(student_id, bytes_earned, f"{lesson_id}-dars testi")
    await update_calf(student_id, 1.0)
    await unlock_next_lesson(student_id, lesson_id)

    await callback.message.edit_text(
        f"\u2705 <b>Tasdiqlandi!</b>\n\n"
        f"\U0001f4da {lesson_id}-dars\n"
        f"\U0001f4ca {score}/{total}\n"
        f"\U0001f4be +{bytes_earned} bayt berildi\n"
        f"\U0001f4d6 {lesson_id + 1}-dars ochildi"
    )

    try:
        await bot.send_message(
            student_id,
            f"\U0001f389 <b>Test tasdiqlandi!</b>\n\n"
            f"\U0001f4da {lesson_id}-dars: {lesson['title'] if lesson else ''}\n"
            f"\U0001f4ca {score}/{total}\n"
            f"\U0001f4be <b>+{bytes_earned} bayt</b>\n"
            f"\U0001f42e Buzoqcha <b>+1 kg</b>\n\n"
            f"\U0001f4d6 {lesson_id + 1}-dars endi ochiq! \U0001f680"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("treject_"))
async def tap_reject(callback: types.CallbackQuery, bot: Bot):
    if callback.from_user.id != TEACHER_ID:
        await callback.answer("Bu tugma faqat ustoz uchun!")
        return
    parts = callback.data.split("_")
    student_id = int(parts[1])
    lesson_id = int(parts[2])

    await callback.message.edit_text(
        f"\u274c <b>Rad etildi</b>\n\n"
        f"\U0001f4da {lesson_id}-dars\n"
        f"O'quvchi qayta topshirishi kerak"
    )

    try:
        await bot.send_message(
            student_id,
            f"\u274c <b>Test rad etildi</b>\n\n"
            f"\U0001f4da {lesson_id}-dars\n"
            f"Qayta urinib ko'ring! \U0001f4aa"
        )
    except Exception:
        pass


# ─────────────────────────────────────────────
# TEZ AYTISH — analogous to DARSLAR TEST
# ─────────────────────────────────────────────

@router.message(Command("tez_aytish"))
async def cmd_tez_aytish(message: types.Message):
    student = await get_student(message.from_user.id)
    if not student or not student.get('is_active'):
        await message.answer(
            "\u26a0\ufe0f Sizda tez aytish kursi ochilmagan.\n"
            "Ustoz bilan bog'laning!"
        )
        return

    access = await get_tez_aytish_access(message.from_user.id)

    if not access:
        await message.answer(
            "\U0001f3a4 Tez aytish darslari hali ochilmagan.\n"
            "Ustoz qo'shgandan so'ng avtomatik ochiladi!"
        )
        return

    text = (
        "\U0001f3a4 <b>Tez Aytish Kursi</b>\n\n"
        "Har bir darsda audio yozing va ustoz tasdiqlaydi!\n"
        "Tasdiqlangandan keyin keyingi dars ochiladi.\n\n"
        "Qaysi darsni ochmoqchisiz?"
    )
    await message.answer(text, reply_markup=tez_aytish_keyboard(access))


@router.callback_query(F.data.startswith("tez_") & ~F.data.startswith("tez_view_"))
async def show_tez_lesson(callback: types.CallbackQuery, state: FSMContext):
    lesson_id = int(callback.data.split("_")[1])

    access = await get_tez_aytish_access(callback.from_user.id)
    acc = next((a for a in access if a['lesson_id'] == lesson_id), None)

    if not acc or acc.get('status') != 'open':
        await callback.answer(
            "\U0001f512 Bu dars hali ochilmagan yoki allaqachon jo'natilgan!",
            show_alert=True
        )
        return

    lesson = get_tez_lesson(lesson_id)
    if not lesson:
        await callback.answer("Dars topilmadi!")
        return

    text = (
        f"\U0001f3a4 <b>{lesson_id}-dars: {lesson['title']}</b>\n\n"
        f"\U0001f4dd <b>Matn:</b>\n<i>{lesson['text']}</i>\n\n"
        f"\U0001f399 Shu matnni to'g'ri va aniq o'qib, audio yuboring!\n\n"
        f"\U0001f4de Audiongizni yuboring:"
    )
    await state.set_state(TezAytishStates.waiting_voice)
    await state.update_data(tez_lesson_id=lesson_id)

    from aiogram.utils.keyboard import InlineKeyboardBuilder as IKB
    builder = IKB()
    builder.button(text="\u274c Bekor qilish", callback_data="tez_cancel")
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("tez_view_"))
async def show_tez_status(callback: types.CallbackQuery):
    lesson_id = int(callback.data.split("_")[2])

    access = await get_tez_aytish_access(callback.from_user.id)
    acc = next((a for a in access if a['lesson_id'] == lesson_id), None)

    if not acc:
        await callback.answer("Topilmadi!")
        return

    status = acc.get('status', 'locked')
    lesson = get_tez_lesson(lesson_id)
    title = lesson['title'] if lesson else f"{lesson_id}-dars"

    if status == 'pending':
        msg = f"\u23f3 {lesson_id}-dars: <b>{title}</b>\n\nAudio jo'natildi, ustoz tekshirmoqda..."
    elif status == 'done':
        msg = f"\u2705 {lesson_id}-dars: <b>{title}</b>\n\nBajarildi!"
    elif status == 'locked':
        msg = f"\U0001f512 {lesson_id}-dars hali ochilmagan."
    else:
        msg = f"\U0001f4cc {lesson_id}-dars: {status}"

    await callback.answer(msg, show_alert=True)


@router.message(TezAytishStates.waiting_voice, F.voice)
async def receive_tez_voice(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    lesson_id = data.get('tez_lesson_id')

    if not lesson_id:
        await state.clear()
        return

    voice_file_id = message.voice.file_id
    student = await get_student(message.from_user.id)
    student_name = student['full_name'] if student else message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"

    submission_id = await submit_tez_aytish_voice(message.from_user.id, lesson_id, voice_file_id)

    lesson = get_tez_lesson(lesson_id)

    await message.answer(
        f"\u2705 <b>Audio qabul qilindi!</b>\n\n"
        f"\U0001f3a4 {lesson_id}-dars: <b>{lesson['title'] if lesson else ''}</b>\n\n"
        f"\u23f3 Ustoz tekshirgandan so'ng keyingi dars ochiladi!\n"
        f"\U0001f514 Natija haqida xabardor bo'lasiz."
    )

    # Send to teacher
    from aiogram.utils.keyboard import InlineKeyboardBuilder as IKB
    builder = IKB()
    builder.button(
        text="\u2705 Tasdiqlash",
        callback_data=f"taz_ok_{submission_id}_{message.from_user.id}_{lesson_id}"
    )
    builder.button(
        text="\u274c Rad etish",
        callback_data=f"taz_no_{submission_id}_{message.from_user.id}_{lesson_id}"
    )
    builder.adjust(2)

    try:
        await bot.send_voice(
            TEACHER_ID,
            voice=voice_file_id,
            caption=(
                f"\U0001f3a4 <b>Tez aytish topshirildi</b>\n\n"
                f"\U0001f464 {student_name} ({username})\n"
                f"\U0001f4da {lesson_id}-dars: {lesson['title'] if lesson else ''}\n\n"
                f"Audioni tinglang va tasdiqlang:"
            ),
            reply_markup=builder.as_markup()
        )
    except Exception:
        pass

    await state.clear()


@router.message(TezAytishStates.waiting_voice)
async def wrong_tez_input(message: types.Message):
    await message.answer(
        "\U0001f399 Iltimos, <b>audio xabar</b> yuboring!\n"
        "Mikrofon tugmasini bosing va gapiring."
    )


@router.callback_query(F.data == "tez_cancel")
async def tez_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("\u274c Bekor qilindi. /tez_aytish — qayta boshlash")
    await callback.answer()
