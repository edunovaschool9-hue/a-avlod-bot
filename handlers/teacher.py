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
)

from config import TEACHER_ID

router = Router()


class RenameStudentStates(StatesGroup):
        waiting_new_name = State()


def is_teacher(user_id):
        return user_id == TEACHER_ID


@router.message(Command("students"))
async def cmd_students(message: types.Message):
        if not is_teacher(message.from_user.id):
                        await message.answer("Bu buyruq faqat ustoz uchun.")
                        return

        students = await get_all_students()

        if not students:
                text = "📭 Hozircha o'quvchilar yo'q."
        else:
                text = f"👥 <b>O'quvchilar ro'yxati ({len(students)} ta):</b>\n\n"
                for i, s in enumerate(students, 1):
                                status = "✅" if s.get('is_active') else "⏳"
                                username = f"@{s['username']}" if s.get('username') else "username yo'q"
                                text += (
                                f"{i}. {status} <b>{s['full_name']}</b>\n"
                                f"   👤 {username}\n"
                                f"   💾 {s.get('bytes_balance', 0)} bayt | "
                                f"💰 {s.get('som_balance', 0):,} so'm | "
                                f"🐮 {s.get('calf_kg', 0)} kg\n\n"
                                )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                                        InlineKeyboardButton(text="➕ O'quvchi qo'shish", callback_data="add_student_help"),
                                        InlineKeyboardButton(text="🗑 O'quvchi o'chirish", callback_data="delete_student_help"),
                        ],
                        [
                                        InlineKeyboardButton(text="✏️ Ismni o'zgartirish", callback_data="rename_student_help"),
                                        InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_students"),
                        ]
        ])

        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "refresh_students")
async def refresh_students(callback: CallbackQuery):
        if not is_teacher(callback.from_user.id):
                        await callback.answer("Ruxsat yo'q!", show_alert=True)
                        return

        students = await get_all_students()

        if not students:
                text = "📭 Hozircha o'quvchilar yo'q."
        else:
                text = f"👥 <b>O'quvchilar ro'yxati ({len(students)} ta):</b>\n\n"
                for i, s in enumerate(students, 1):
                                status = "✅" if s.get('is_active') else "⏳"
                                username = f"@{s['username']}" if s.get('username') else "username yo'q"
                                text += (
                                f"{i}. {status} <b>{s['full_name']}</b>\n"
                                f"   👤 {username}\n"
                                f"   💾 {s.get('bytes_balance', 0)} bayt | "
                                f"💰 {s.get('som_balance', 0):,} so'm | "
                                f"🐮 {s.get('calf_kg', 0)} kg\n\n"
                                )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [
                                        InlineKeyboardButton(text="➕ O'quvchi qo'shish", callback_data="add_student_help"),
                                        InlineKeyboardButton(text="🗑 O'quvchi o'chirish", callback_data="delete_student_help"),
                        ],
                        [
                                        InlineKeyboardButton(text="✏️ Ismni o'zgartirish", callback_data="rename_student_help"),
                                        InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_students"),
                        ]
        ])

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer("✅ Yangilandi!")


@router.callback_query(F.data == "add_student_help")
async def add_student_help(callback: CallbackQuery):
        if not is_teacher(callback.from_user.id):
                        await callback.answer("Ruxsat yo'q!", show_alert=True)
                        return

        text = (
                "➕ <b>O'quvchi qo'shish:</b>\n\n"
                "Quyidagi formatda yozing:\n\n"
                "<code>/add_student @username 500000</code>\n\n"
                "📌 username — o'quvchining Telegram username\n"
                "💰 500000 — kurs narxi (so'm)\n\n"
                "⚠️ O'quvchi avval /start bosgan bo'lishi kerak!"
        )
        await callback.message.answer(text)
        await callback.answer()


# ─────────────────────────────────────────────
#  DELETE STUDENT
# ─────────────────────────────────────────────

@router.callback_query(F.data == "delete_student_help")
async def delete_student_help(callback: CallbackQuery):
        if not is_teacher(callback.from_user.id):
                        await callback.answer("Ruxsat yo'q!", show_alert=True)
                        return

        students = await get_all_students()

        if not students:
                await callback.message.answer("📭 O'chirish uchun o'quvchilar yo'q.")
                await callback.answer()
                return

        text = "🗑 <b>Qaysi o'quvchini o'chirmoqchisiz?</b>\n\nQuyidagi ro'yxatdan tanlang:"

        buttons = []
        for s in students[:10]:
                username = s.get('username') or str(s['telegram_id'])
                label = f"🗑 {s['full_name']} (@{username})"
                buttons.append([InlineKeyboardButton(
                        text=label,
                        callback_data=f"delconfirm_{s['telegram_id']}"
                )])

        buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()


@router.callback_query(F.data.startswith("delconfirm_"))
async def del_confirm(callback: CallbackQuery, bot: Bot):
        if not is_teacher(callback.from_user.id):
                        await callback.answer("Ruxsat yo'q!", show_alert=True)
                        return

        telegram_id = int(callback.data[len("delconfirm_"):])

        from database import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
                student = await conn.fetchrow(
                                "SELECT * FROM students WHERE telegram_id = $1", telegram_id
                )
                if not student:
                        await callback.answer("O'quvchi topilmadi!", show_alert=True)
                        return

        name = student['full_name']
        username = student.get('username', '') or ''

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                                InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"delyes_{telegram_id}"),
                                InlineKeyboardButton(text="❌ Yo'q", callback_data="cancel_action"),
                ]
        ])

        await callback.message.answer(
                f"⚠️ <b>Rostdan ham o'chirasizmi?</b>\n\n"
                f"👤 {name} (@{username})\n\n"
                f"Bu amal qaytarib bo'lmaydi!",
                reply_markup=keyboard
        )
        await callback.answer()


@router.callback_query(F.data.startswith("delyes_"))
async def del_yes(callback: CallbackQuery, bot: Bot):
        if not is_teacher(callback.from_user.id):
                        await callback.answer("Ruxsat yo'q!", show_alert=True)
                        return

        telegram_id = int(callback.data[len("delyes_"):])

        from database import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
                student = await conn.fetchrow(
                                "SELECT * FROM students WHERE telegram_id = $1", telegram_id
                )
                if not student:
                                await callback.answer("O'quvchi topilmadi!", show_alert=True)
                                return

                name = student['full_name']
                username = student.get('username', '') or ''

        await conn.execute("DELETE FROM lesson_access WHERE student_id = $1", telegram_id)
        await conn.execute("DELETE FROM bytes_transactions WHERE student_id = $1", telegram_id)
        await conn.execute("DELETE FROM som_transactions WHERE student_id = $1", telegram_id)
        await conn.execute("DELETE FROM homeworks WHERE student_id = $1", telegram_id)
        await conn.execute("DELETE FROM students WHERE telegram_id = $1", telegram_id)

        await callback.message.edit_text(
                f"✅ <b>O'quvchi o'chirildi!</b>\n\n"
                f"👤 {name} (@{username})"
        )

        try:
                await bot.send_message(
                                telegram_id,
                                "❌ Sizning hisobingiz o'chirildi.\n"
                                "Batafsil ma'lumot uchun ustoz bilan bog'laning."
                )
        except Exception:
                pass

        await callback.answer("✅ O'chirildi!")


# ─────────────────────────────────────────────
#  RENAME STUDENT
# ─────────────────────────────────────────────

@router.callback_query(F.data == "rename_student_help")
async def rename_student_help(callback: CallbackQuery):
        if not is_teacher(callback.from_user.id):
                        await callback.answer("Ruxsat yo'q!", show_alert=True)
                        return

        students = await get_all_students()

        if not students:
                await callback.message.answer("📭 O'quvchilar yo'q.")
                await callback.answer()
                return

        text = "✏️ <b>Qaysi o'quvchining ismini o'zgartirasiz?</b>"

        buttons = []
        for s in students[:10]:
                username = s.get('username') or str(s['telegram_id'])
                label = f"✏️ {s['full_name']} (@{username})"
                buttons.append([InlineKeyboardButton(
                        text=label,
                        callback_data=f"renamepick_{s['telegram_id']}"
                )])

        buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()


@router.callback_query(F.data.startswith("renamepick_"))
async def rename_pick(callback: CallbackQuery, state: FSMContext):
        if not is_teacher(callback.from_user.id):
                        await callback.answer("Ruxsat yo'q!", show_alert=True)
                        return

        telegram_id = int(callback.data[len("renamepick_"):])

        from database import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
                student = await conn.fetchrow(
                                "SELECT * FROM students WHERE telegram_id = $1", telegram_id
                )
                if not student:
                        await callback.answer("O'quvchi topilmadi!", show_alert=True)
                        return

        name = student['full_name']
        username = student.get('username', '') or ''

        await state.set_state(RenameStudentStates.waiting_new_name)
        await state.update_data(rename_telegram_id=telegram_id, old_name=name)

        await callback.message.answer(
                f"✏️ <b>{name}</b> (@{username}) ning yangi ismini yozing:\n\n"
                f"<i>Bekor qilish uchun /cancel yozing</i>"
        )
        await callback.answer()


@router.message(RenameStudentStates.waiting_new_name)
async def process_rename(message: types.Message, state: FSMContext, bot: Bot):
        if not is_teacher(message.from_user.id):
                        await state.clear()
                        return

        new_name = message.text.strip()

        if new_name.startswith('/'):
                await state.clear()
                await message.answer("❌ Bekor qilindi.")
                return

        if len(new_name) < 3 or len(new_name) > 60:
                await message.answer(
                                "❌ Ism 3-60 ta belgidan iborat bo'lishi kerak. Qayta yozing:"
                )
                return

        data = await state.get_data()
        telegram_id = data['rename_telegram_id']
        old_name = data['old_name']

        await update_student_name(telegram_id, new_name)
        await state.clear()

        await message.answer(
                f"✅ <b>Ism muvaffaqiyatli o'zgartirildi!</b>\n\n"
                f"Eski ism: {old_name}\n"
                f"Yangi ism: <b>{new_name}</b>"
        )

        try:
                await bot.send_message(
                                telegram_id,
                                f"✏️ Sizning ismingiz o'zgartirildi.\n"
                                f"Yangi ism: <b>{new_name}</b>"
                )
        except Exception:
                pass


# ─────────────────────────────────────────────
#  CANCEL
# ─────────────────────────────────────────────

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text("❌ Bekor qilindi.")
        await callback.answer()


# ─────────────────────────────────────────────
#  ADD STUDENT COMMAND
# ─────────────────────────────────────────────

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

        await message.answer(
                f"✅ <b>O'quvchi faollashtirildi!</b>\n\n"
                f"👤 {student['full_name']} (@{username})\n"
                f"💰 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
                f"🐮 Buzoqcha: <b>40 kg</b>\n"
                f"📚 1-dars testi ochildi\n\n"
                f"O'quvchiga xabar yuborildi!"
        )

        try:
                await bot.send_message(
                                student['telegram_id'],
                                f"🎉 <b>A Avlod Academy ga xush kelibsiz!</b>\n\n"
                                f"Sizning hisobingiz faollashtirildi!\n\n"
                                f"💰 Asosiy hisob: <b>{som_amount:,} so'm</b>\n"
                                f"🐮 Buzoqchangiz: <b>40 kg</b>\n"
                                f"📚 1-dars testi ochiq!\n\n"
                                f"Akademiyani oching va boshlang! 🚀"
                )
        except Exception:
                pass


@router.message(Command("approve_test"))
async def cmd_approve_test(message: types.Message, bot: Bot):

        if not is_teacher(message.from_user.id):
                        await message.answer("Bu buyruq faqat ustoz uchun.")
                        return

        parts = message.text.split()

        if len(parts) < 3:
                await message.answer(
                                "<code>/approve_test @username 1</code>\n"
                                "(username va lesson_id)"
                )
                return

        username = parts[1].lstrip('@')

        try:
                lesson_id = int(parts[2])
        except ValueError:
                await message.answer("Dars raqami son bolishi kerak.")
                return

        student = await get_student_by_username(username)

        if not student:
                await message.answer(f"@{username} topilmadi.")
                return

        bytes_earned = 25

        await add_bytes(
                student['telegram_id'],
                bytes_earned,
                f"{lesson_id}-dars testi"
        )

        await update_calf(student['telegram_id'], 1.0)

        await unlock_next_lesson(student['telegram_id'], lesson_id)

        await message.answer(
                f"✅ {lesson_id}-dars testi tasdiqlandi!\n"
                f"👤 {student['full_name']}\n"
                f"+{bytes_earned} bayt, +1 kg\n"
                f"{lesson_id + 1}-dars testi ochildi"
        )

        try:
                await bot.send_message(
                                student['telegram_id'],
                                f"🎉 <b>Test tasdiqlandi!</b>\n\n"
                                f"📚 {lesson_id}-dars testi\n"
                                f"💾 <b>+{bytes_earned} bayt</b>\n"
                                f"🐮 Buzoqcha <b>+1 kg</b> oldi!\n\n"
                                f"📖 {lesson_id + 1}-dars testi endi ochiq!\n"
                                f"Akademiyani oching! 🚀"
                )
        except Exception:
                pass


@router.message(Command("warn"))
async def cmd_warn(message: types.Message, bot: Bot):

        if not is_teacher(message.from_user.id):
                        return

        parts = message.text.split(maxsplit=2)

        if len(parts) < 2:
                await message.answer(
                                "<code>/warn @username sabab</code>"
                )
                return

        username = parts[1].lstrip('@')

        reason = (
                parts[2]
                if len(parts) > 2
                else "Vazifa bajarilmadi"
        )

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

        await update_calf(
                student['telegram_id'],
                -kg_penalty
        )

        if som_penalty:
                await add_som(
                                student['telegram_id'],
                                -som_penalty,
                                f"Jarima: {reason}"
                )

        from database import add_warning

        await add_warning(student['telegram_id'])

        penalty_text = (
                f"💰 -{som_penalty:,} so'm jarima"
                if som_penalty
                else ""
        )

        await message.answer(
                f"⚠️ Ogohlantirish #{warnings}\n"
                f"👤 {student['full_name']}\n"
                f"🐮 -{kg_penalty} kg\n"
                f"{penalty_text}"
        )

        try:
                msg = (
                                f"⚠️ <b>Ogohlantirish #{warnings}</b>\n\n"
                                f"Sabab: {reason}\n"
                                f"🐮 Buzoqcha -{kg_penalty} kg yo'qotdi"
                )

        if som_penalty:
                        msg += f"\n💰 -{som_penalty:,} so'm jarima"

        await bot.send_message(
                        student['telegram_id'],
                        msg
        )

        except Exception:
        pass
