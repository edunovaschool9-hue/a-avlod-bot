from aiogram import Router, types, Bot
from aiogram.filters import Command
from database import get_all_students, add_bytes, find_student_by_username
from config import TEACHER_ID

router = Router()

def is_teacher(user_id: int) -> bool:
      return user_id == TEACHER_ID

@router.message(Command("students"))
async def cmd_students(message: types.Message):
      if not is_teacher(message.from_user.id):
                await message.answer("Bu buyruq faqat ustoz uchun.")
                return

      students = await get_all_students()
      if not students:
                await message.answer("Hali hech kim royxatdan otmagan.")
                return

      text = f"👥 <b>Jami: {len(students)}</b>\n\n"
      for i, s in enumerate(students[:20], 1):
                username = f"@{s['username']}" if s['username'] else "—"
                text += f"{i}. {s['full_name']} ({username}) — <b>{s['bytes_balance']}</b> bayt\n"

      await message.answer(text)

@router.message(Command("add_bytes"))
async def cmd_add_bytes(message: types.Message, bot: Bot):
      if not is_teacher(message.from_user.id):
                await message.answer("Bu buyruq faqat ustoz uchun.")
                return

      parts = message.text.split(maxsplit=3)
      if len(parts) < 3:
                await message.answer(
                              "Noto'g'ri format.\n\n"
                              "<b>Ishlatish:</b>\n"
                              "<code>/add_bytes @username 50 sabab</code>"
                )
                return

      username = parts[1]
      try:
                amount = int(parts[2])
except ValueError:
        await message.answer("Miqdor son bolishi kerak.")
        return

    if amount <= 0:
              await message.answer("Miqdor 0 dan katta bolishi kerak.")
              return

    reason = parts[3] if len(parts) > 3 else "Ustoz tomonidan qoshildi"

    student = await find_student_by_username(username)
    if not student:
              await message.answer(f"{username} topilmadi.")
              return

    success = await add_bytes(student['telegram_id'], amount, reason)
    if not success:
              await message.answer("Xatolik yuz berdi.")
              return

    await message.answer(
              f"✅ {student['full_name']} ga <b>{amount}</b> bayt qoshildi\n"
              f"Sabab: {reason}\n"
              f"Yangi balans: <b>{student['bytes_balance'] + amount}</b>"
    )

    try:
              await bot.send_message(
                            student['telegram_id'],
                            f"🎉 Sizga <b>+{amount} bayt</b> qoshildi!\n"
                            f"Sabab: {reason}\n"
                            f"Yangi balans: <b>{student['bytes_balance'] + amount} bayt</b>"
              )
except Exception:
          pass

@router.message(Command("sub_bytes"))
async def cmd_sub_bytes(message: types.Message, bot: Bot):
      if not is_teacher(message.from_user.id):
                await message.answer("Bu buyruq faqat ustoz uchun.")
                return

      parts = message.text.split(maxsplit=3)
      if len(parts) < 3:
                await message.answer(
                              "Noto'g'ri format.\n\n"
                              "<b>Ishlatish:</b>\n"
                              "<code>/sub_bytes @username 30 sabab</code>"
                )
                return

      username = parts[1]
      try:
                amount = int(parts[2])
except ValueError:
        await message.answer("Miqdor son bolishi kerak.")
        return

    if amount <= 0:
              await message.answer("Miqdor 0 dan katta bolishi kerak.")
              return

    reason = parts[3] if len(parts) > 3 else "Ustoz tomonidan ayirildi"

    student = await find_student_by_username(username)
    if not student:
              await message.answer(f"{username} topilmadi.")
              return

    success = await add_bytes(student['telegram_id'], -amount, reason)
    if not success:
              await message.answer(
                            f"Xatolik. Balans yetarli emas.\n"
                            f"Joriy balans: {student['bytes_balance']}"
              )
              return

    await message.answer(
              f"✅ {student['full_name']} dan <b>{amount}</b> bayt ayirildi\n"
              f"Sabab: {reason}"
    )

    try:
              await bot.send_message(
                            student['telegram_id'],
                            f"➖ Hisobingizdan <b>{amount} bayt</b> ayirildi\n"
                            f"Sabab: {reason}"
              )
except Exception:
          pass

@router.message(Command("stats"))
async def cmd_stats(message: types.Message):
      if not is_teacher(message.from_user.id):
                await message.answer("Bu buyruq faqat ustoz uchun.")
                return

      students = await get_all_students()
      total = len(students)
      total_bytes = sum(s['bytes_balance'] for s in students)
      avg = total_bytes // total if total > 0 else 0

    text = (
              f"📊 <b>A Avlod Academy statistikasi</b>\n\n"
              f"👥 Oquvchilar: <b>{total}</b>\n"
              f"💾 Jami bayt: <b>{total_bytes}</b>\n"
              f"📈 Ortacha balans: <b>{avg}</b>\n"
    )

    if students:
              top = sorted(students, key=lambda s: s['bytes_balance'], reverse=True)[0]
              text += f"\n🏆 Lider: <b>{top['full_name']}</b> ({top['bytes_balance']} bayt)"

    await message.answer(text)
