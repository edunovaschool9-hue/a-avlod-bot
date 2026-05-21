from aiogram import Router, types, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_student, add_bytes, get_lesson_access, unlock_next_lesson, update_calf
from config import TEACHER_ID
from lessons_data import MONTHLY_LESSONS

router = Router()


class TestStates(StatesGroup):
    answering = State()


def get_lesson(lesson_id: int):
    for lesson in MONTHLY_LESSONS:
        if lesson["id"] == lesson_id:
            return lesson
    return None


def lesson_keyboard():
    builder = InlineKeyboardBuilder()
    for lesson in MONTHLY_LESSONS:
        builder.button(
            text=f"📚 {lesson['id']}-dars: {lesson['title']}",
            callback_data=f"lesson_{lesson['id']}"
        )
    builder.adjust(1)
    return builder.as_markup()


def lesson_blocks_keyboard(lesson_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🧪 Test boshlash (+25 bayt)", callback_data=f"test_{lesson_id}_0")
    builder.button(text="🎬 Video darslik (tez orada)", callback_data="coming_soon")
    builder.button(text="✍️ Insho / Topshiriq (tez orada)", callback_data="coming_soon")
    builder.button(text="⬅️ Darslarga qaytish", callback_data="back_lessons")
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
    text = (
        "📚 <b>1 Oylik Darslar Rejasi</b>\n\n"
        "Haftada 2 marta dars — 4 hafta, 8 ta dars!\n"
        "Har bir darsda test yechib <b>25 bayt</b> ishlang!\n\n"
        "Qaysi darsni ochmoqchisiz?"
    )
    await message.answer(text, reply_markup=lesson_keyboard())


@router.callback_query(F.data == "back_lessons")
async def back_to_lessons(callback: types.CallbackQuery):
    text = (
        "📚 <b>1 Oylik Darslar Rejasi</b>\n\n"
        "Haftada 2 marta dars — 4 hafta, 8 ta dars!\n"
        "Har bir darsda test yechib <b>25 bayt</b> ishlang!\n\n"
        "Qaysi darsni ochmoqchisiz?"
    )
    await callback.message.edit_text(text, reply_markup=lesson_keyboard())


@router.callback_query(F.data == "coming_soon")
async def coming_soon(callback: types.CallbackQuery):
    await callback.answer("⏳ Bu bo'lim tez orada ochiladi!", show_alert=True)


@router.callback_query(F.data.startswith("lesson_"))
async def show_lesson(callback: types.CallbackQuery):
    lesson_id = int(callback.data.split("_")[1])
    lesson = get_lesson(lesson_id)
    if not lesson:
        await callback.answer("Dars topilmadi!")
        return
    text = (
        f"📚 <b>{lesson['id']}-dars: {lesson['title']}</b>\n"
        f"📅 {lesson['week']}-hafta\n\n"
        f"{lesson['description']}\n\n"
        f"🧪 Test — 5 savol = <b>25 bayt</b>\n"
        f"🎬 Video darslik — <i>tez orada</i>\n"
        f"✍️ Insho — <i>tez orada</i>"
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
        f"🧪 <b>{lesson['title']}</b>\n"
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
        feedback = "✅ To'g'ri!"
    else:
        correct_text = question["options"][correct]
        feedback = f"❌ Noto'g'ri! To'g'ri: <b>{correct_text}</b>"
    next_idx = question_idx + 1
    if next_idx < total:
        await state.update_data(score=score)
        next_question = lesson["tests"][next_idx]
        text = (
            f"🧪 <b>{lesson['title']}</b>\n"
            f"Savol {next_idx + 1}/{total}\n\n"
            f"{feedback}\n\n"
            f"<b>{next_question['question']}</b>"
        )
        await callback.message.edit_text(
            text,
            reply_markup=answer_keyboard(lesson_id, next_idx, next_question["options"])
        )
    else:
        await state.clear()
        bytes_earned = score * 5
        student = await get_student(callback.from_user.id)
        student_name = student['full_name'] if student else callback.from_user.full_name
        username = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{callback.from_user.id}"
        if score == total:
            emoji = "🏆 Mukammal!"
        elif score >= total * 0.8:
            emoji = "⭐ A'lo!"
        elif score >= total * 0.6:
            emoji = "👍 Yaxshi!"
        else:
            emoji = "💪 Davom eting!"

        await callback.message.edit_text(
            f"🎉 <b>Test yakunlandi!</b>\n\n"
            f"{emoji}\n\n"
            f"📊 Natija: <b>{score}/{total}</b>\n"
            f"💾 Kutilayotgan bayt: <b>+{bytes_earned}</b>\n\n"
            f"⏳ O'qituvchi tekshirmoqda..."
        )

        # Ustozga 2 ta tugma yuborish
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"✅ Tasdiqlash (+{bytes_earned} bayt)",
            callback_data=f"tapprove_{callback.from_user.id}_{lesson_id}_{bytes_earned}_{score}_{total}"
        )
        builder.button(
            text="❌ Rad etish",
            callback_data=f"treject_{callback.from_user.id}_{lesson_id}"
        )
        builder.adjust(1)

        await bot.send_message(
            TEACHER_ID,
            f"📋 <b>Yangi test natijasi!</b>\n\n"
            f"👤 {student_name} ({username})\n"
            f"📚 {lesson_id}-dars: {lesson['title']}\n"
            f"📊 Natija: <b>{score}/{total}</b> — {emoji}\n"
            f"💾 Mukofot: <b>+{bytes_earned} bayt</b>",
            reply_markup=builder.as_markup()
        )


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
        f"✅ <b>Tasdiqlandi!</b>\n\n"
        f"📚 {lesson_id}-dars\n"
        f"📊 {score}/{total}\n"
        f"💾 +{bytes_earned} bayt berildi\n"
        f"📖 {lesson_id + 1}-dars ochildi"
    )

    try:
        await bot.send_message(
            student_id,
            f"🎉 <b>Test tasdiqlandi!</b>\n\n"
            f"📚 {lesson_id}-dars: {lesson['title'] if lesson else ''}\n"
            f"📊 {score}/{total}\n"
            f"💾 <b>+{bytes_earned} bayt</b>\n"
            f"🐮 Buzoqcha <b>+1 kg</b>\n\n"
            f"📖 {lesson_id + 1}-dars endi ochiq! 🚀"
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
        f"❌ <b>Rad etildi</b>\n\n"
        f"📚 {lesson_id}-dars\n"
        f"O'quvchi qayta topshirishi kerak"
    )

    try:
        await bot.send_message(
            student_id,
            f"❌ <b>Test rad etildi</b>\n\n"
            f"📚 {lesson_id}-dars testini qayta topshiring.\n"
            f"Yaxshiroq tayyorlaning! 💪"
        )
    except Exception:
        pass
