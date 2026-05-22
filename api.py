from aiohttp import web
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import get_student, get_transactions, get_student_homeworks, get_lesson_access, add_bytes, unlock_next_lesson, update_calf, get_tez_aytish_access, submit_tez_aytish_voice, approve_tez_aytish, reject_tez_aytish
from lessons_data import MONTHLY_LESSONS, TEZ_AYTISH_LESSONS
from config import BOT_TOKEN, TEACHER_ID

routes = web.RouteTableDef()
pending_tests = {}


def get_uid(request):
    return request.rel_url.query.get("user_id")


@routes.get("/api/profile")
async def get_profile(request):
    uid = get_uid(request)
    if not uid:
        return web.json_response({"error": "No user_id"}, status=400)
    student = await get_student(int(uid))
    if not student:
        return web.json_response({"error": "Not registered"}, status=404)
    transactions = await get_transactions(int(uid), limit=1000)
    total_earned = sum(t["amount"] for t in transactions if t["amount"] > 0)
    homeworks = await get_student_homeworks(int(uid))
    return web.json_response({
        "id": student["telegram_id"],
        "full_name": student["full_name"],
        "username": student["username"],
        "bytes_balance": student["bytes_balance"],
        "som_balance": student.get("som_balance", 0),
        "calf_kg": student.get("calf_kg", 40),
        "level": student["level"],
        "rank": student["rank"],
        "streak_days": student["streak_days"],
        "is_active": student.get("is_active", 0),
        "warnings": student.get("warnings", 0),
        "total_earned": total_earned,
        "homeworks_done": len([h for h in homeworks if h["status"] == "done"]),
        "homeworks_active": len([h for h in homeworks if h["status"] == "new"]),
    })


@routes.get("/api/lesson_access")
async def get_access(request):
    uid = get_uid(request)
    if not uid:
        return web.json_response({"error": "No user_id"}, status=400)
    try:
        access = await get_lesson_access(int(uid))
        return web.json_response({"access": access})
    except Exception as e:
        print(f"lesson_access error: {e}")
        return web.json_response({"access": []})


@routes.get("/api/lessons")
async def get_lessons(request):
    lessons = []
    for l in MONTHLY_LESSONS:
        lessons.append({
            "id": l["id"],
            "title": l["title"],
            "week": l["week"],
            "description": l["description"],
            "tests_count": len(l["tests"]),
            "bytes_reward": len(l["tests"]) * 5,
        })
    return web.json_response({"lessons": lessons})


@routes.get("/api/lessons/{lesson_id}")
async def get_lesson(request):
    lid = int(request.match_info["lesson_id"])
    lesson = next((l for l in MONTHLY_LESSONS if l["id"] == lid), None)
    if not lesson:
        return web.json_response({"error": "Not found"}, status=404)
    tests = [{"index": i, "question": t["question"], "options": t["options"]}
             for i, t in enumerate(lesson["tests"])]
    return web.json_response({
        "id": lesson["id"],
        "title": lesson["title"],
        "week": lesson["week"],
        "description": lesson["description"],
        "tests": tests
    })


@routes.post("/api/lessons/{lesson_id}/submit")
async def submit_test(request):
    lid = int(request.match_info["lesson_id"])
    lesson = next((l for l in MONTHLY_LESSONS if l["id"] == lid), None)
    if not lesson:
        return web.json_response({"error": "Not found"}, status=404)

    data = await request.json()
    uid = data.get("user_id")
    answers = data.get("answers", [])
    if not uid:
        return web.json_response({"error": "No user_id"}, status=400)

    score = sum(
        1 for i, a in enumerate(answers)
        if i < len(lesson["tests"]) and a == lesson["tests"][i]["correct"]
    )
    total = len(lesson["tests"])
    bytes_earned = score * 5

    student = await get_student(int(uid))
    student_name = student["full_name"] if student else f"ID:{uid}"
    username = f"@{student['username']}" if student and student.get('username') else f"ID:{uid}"

    key = f"{uid}_{lid}"
    pending_tests[key] = {
        "student_id": int(uid),
        "student_name": student_name,
        "lesson_id": lid,
        "score": score,
        "total": total,
        "bytes_earned": bytes_earned,
    }

    if score == total:
        emoji = "🏆 Mukammal!"
    elif score >= total * 0.8:
        emoji = "⭐ A'lo!"
    elif score >= total * 0.6:
        emoji = "👍 Yaxshi!"
    else:
        emoji = "💪 Davom eting!"

    # Ustozga kнопки yuborish
    try:
        bot = Bot(token=BOT_TOKEN)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"tapprove_{uid}_{lid}_{bytes_earned}_{score}_{total}"
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"treject_{uid}_{lid}"
                )
            ]
        ])
        await bot.send_message(
            TEACHER_ID,
            f"📋 <b>Yangi test natijasi!</b>\n\n"
            f"👤 {student_name} ({username})\n"
            f"📚 {lid}-dars: {lesson['title']}\n"
            f"📊 Natija: <b>{score}/{total}</b> — {emoji}\n"
            f"💾 Mukofot: <b>+{bytes_earned} bayt</b>",
            reply_markup=keyboard
        )
        await bot.session.close()
    except Exception as e:
        print(f"Xato: {e}")

    return web.json_response({
        "success": True,
        "score": score,
        "total": total,
        "bytes_earned": bytes_earned,
        "result_emoji": emoji,
    })


@routes.get("/api/homeworks")
async def get_homeworks(request):
    uid = get_uid(request)
    if not uid:
        return web.json_response({"error": "No user_id"}, status=400)
    homeworks = await get_student_homeworks(int(uid))
    return web.json_response({"homeworks": homeworks})


@routes.get("/api/transactions")
async def get_trans(request):
    uid = get_uid(request)
    if not uid:
        return web.json_response({"error": "No user_id"}, status=400)
    transactions = await get_transactions(int(uid), limit=20)
    return web.json_response({"transactions": transactions})



# ===== TEZ AYTISH API =====

@routes.get("/api/tez_aytish/lessons")
async def get_tez_aytish_lessons(request):
        uid = get_uid(request)
        if not uid:
                    return web.json_response({"error": "No user_id"}, status=400)
                try:
                            access = await get_tez_aytish_access(int(uid))
                            access_map = {a["lesson_id"]: a for a in access}
                            lessons = []
                            for l in TEZ_AYTISH_LESSONS:
                                            a = access_map.get(l["id"])
                                            lessons.append({
                                                                "id": l["id"],
                                                                "week": l["week"],
                                                                "title": l["title"],
                                                                "text": l["text"],
                                                                "hint": l["hint"],
                                                                "status": a["status"] if a else "locked",
                                            })
                                        return web.json_response({"lessons": lessons})
except Exception as e:
        print(f"tez_aytish lessons error: {e}")
        return web.json_response({"lessons": []})

@routes.post("/api/tez_aytish/{lesson_id}/submit_voice")
async def submit_tez_aytish(request):
        lid = int(request.match_info["lesson_id"])
    data = await request.json()
    uid = data.get("user_id")
    voice_file_id = data.get("voice_file_id")
    if not uid or not voice_file_id:
                return web.json_response({"error": "Missing data"}, status=400)
    try:
                lesson = next((l for l in TEZ_AYTISH_LESSONS if l["id"] == lid), None)
        if not lesson:
                        return web.json_response({"error": "Lesson not found"}, status=404)
        student = await get_student(int(uid))
        student_name = student["full_name"] if student else f"ID:{uid}"
        username = f"@{student['username']}" if student and student.get('username') else f"ID:{uid}"
        submission_id = await submit_tez_aytish_voice(int(uid), lid, voice_file_id)
        # Notify teacher
        bot = Bot(token=BOT_TOKEN)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                                            text="✅ Tasdiqlash",
                                            callback_data=f"taz_ok_{submission_id}_{uid}_{lid}"
                        ),
                        InlineKeyboardButton(
                                            text="❌ Rad etish",
                                            callback_data=f"taz_no_{submission_id}_{uid}_{lid}"
                        )
        ]])
        await bot.send_voice(
                        TEACHER_ID,
                        voice=voice_file_id,
                        caption=f"🎤 <b>Tez aytish yuborildi!</b>\n\n"
                                f"👤 {student_name} ({username})\n"
                                f"📚 {lid}-dars: {lesson['title']}\n"
                                f"📝 <i>{lesson['text']}</i>",
                        reply_markup=keyboard
        )
        await bot.session.close()
        return web.json_response({"success": True, "submission_id": submission_id})
except Exception as e:
        print(f"tez_aytish submit error: {e}")
        return web.json_response({"error": str(e)}, status=500)



@routes.post("/api/upload_voice")
async def upload_voice(request):
        try:
                    reader = await request.multipart()
                    uid = None
                    voice_data = None
                    async for field in reader:
                                    if field.name == 'user_id':
                                                        uid = await field.read(decode=True)
                                                        uid = uid.decode() if uid else None
                                    elif field.name == 'voice':
                                                        voice_data = await field.read()
                                                if not voice_data:
                                                                return web.json_response({"error": "No voice data"}, status=400)
                                                            bot = Bot(token=BOT_TOKEN)
                                from aiogram.types import BufferedInputFile
                    voice_file = BufferedInputFile(voice_data, filename="voice.ogg")
                    msg = await bot.send_voice(TEACHER_ID, voice=voice_file)
                    file_id = msg.voice.file_id
                    await bot.delete_message(TEACHER_ID, msg.message_id)
                    await bot.session.close()
                    return web.json_response({"file_id": file_id})
except Exception as e:
            print(f"upload_voice error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    
@routes.get("/")
async def index(request):
    return web.FileResponse("static/index.html")


@routes.get("/health")
async def health(request):
    return web.json_response({"status": "ok"})


def create_app():
    app = web.Application()
    app.add_routes(routes)
    app.router.add_static("/static", "static")
    return app
