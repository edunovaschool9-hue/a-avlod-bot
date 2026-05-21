from aiohttp import web
from aiogram import Bot
from database import get_student, get_transactions, get_student_homeworks, get_lesson_access
from lessons_data import MONTHLY_LESSONS
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
    access = await get_lesson_access(int(uid))
    return web.json_response({"access": access})


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

    # Serverda tekshirish
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
        "username": username,
        "lesson_id": lid,
        "lesson_title": lesson["title"],
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

    # Ustozga xabar yuborish
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            TEACHER_ID,
            f"📋 <b>Yangi test natijasi!</b>\n\n"
            f"👤 O'quvchi: {student_name} ({username})\n"
            f"📚 Dars: {lid}-dars — {lesson['title']}\n"
            f"📊 Natija: <b>{score}/{total}</b>\n"
            f"💾 Mukofot: <b>+{bytes_earned} bayt</b>\n\n"
            f"Tasdiqlash uchun:\n"
            f"<code>/approve_test {username} {lid}</code>"
        )
        await bot.session.close()
    except Exception as e:
        print(f"Ustoz xabardor qilinmadi: {e}")

    return web.json_response({
        "success": True,
        "score": score,
        "total": total,
        "bytes_earned": bytes_earned,
        "result_emoji": emoji,
        "pending_key": key,
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
