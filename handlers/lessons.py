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
            f"📖 {lesson_id + 1}-dars endi ochiq!\n"
            f"Akademiyani oching! 🚀"
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
            f"Yaxshiroq tayyorlaning va qayta urining! 💪"
        )
    except Exception:
        pass
