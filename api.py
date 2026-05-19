"""
API server for Telegram Mini App.
"""

import hmac
import hashlib
import json
from urllib.parse import parse_qs
from aiohttp import web
from database import get_student, get_transactions, get_student_homeworks
from config import BOT_TOKEN
from lessons_data import MONTHLY_LESSONS

routes = web.RouteTableDef()
pending_tests = {}


def get_user_id(request):
    return request.rel_url.query.get("user_id")


@routes.get("/api/profile")
async def get_profile(request):
    user_id = get_user_id(request)
    if not user_id:
        return web.json_response({"error": "No user_id"}, status=400)
    student = await get_student(int(user_id))
    if not student:
        return web.json_response({"error": "Not registered"}, status=404)
    transactions = await get_transactions(int(user_id), limit=1000)
    total_earned = sum(t["amount"] for t in transactions if t["amount"] > 0)
    homeworks = await get_student_homeworks(int(user_id))
    return web.json_response({
        "id": student["telegram_id"],
        "full_name": student["full_name"],
        "username": student["username"],
        "bytes_balance": student["bytes_balance"],
        "level": student["level"],
        "rank": student["rank"],
        "streak_days": student["streak_days"],
        "total_earned": total_earned,
        "homeworks_done": len([h for h in homeworks if h["status"] == "done"]),
        "homeworks_active": len([h for h in homeworks if h["status"] == "new"]),
    })


@routes.get("/api/homeworks")
async def get_homeworks(request):
    user_id = get_user_id(request)
    if not user_id:
        return web.json_response({"error": "No user_id"}, status=400)
    homeworks = await get_student_homeworks(int(user_id))
    return web.json_response({"homeworks": homeworks})


@routes.get("/api/transactions")
async def get_trans(request):
    user_id = get_user_id(request)
    if not user_id:
        return web.json_response({"error": "No user_id"}, status=400)
    transactions = await get_transactions(int(user_id), limit=20)
    return web.json_response({"transactions": transactions})


@routes.get("/api/lessons")
async def get_lessons(request):
    lessons = []
    for lesson in MONTHLY_LESSONS:
        lessons.append({
            "id": lesson["id"],
            "title": lesson["title"],
            "week": lesson["week"],
            "description": lesson["description"],
            "tests_count": len(lesson["tests"]),
            "bytes_reward": len(lesson["tests"]) * 5,
        })
    return web.json_response({"lessons": lessons})


@routes.get("/api/lessons/{lesson_id}")
async def get_lesson(request):
    lesson_id = int(request.match_info["lesson_id"])
    lesson = next((l for l in MONTHLY_LESSONS if l["id"] == lesson_id), None)
    if not lesson:
        return web.json_response({"error": "Not found"}, status=404)
    tests = [{"index": i, "question": t["question"], "options": t["options"]} for i, t in enumerate(lesson["tests"])]
    return web.json_response({
        "id": lesson["id"],
        "title": lesson["title"],
        "week": lesson["week"],
        "description": lesson["description"],
        "tests": tests,
    })


@routes.post("/api/lessons/{lesson_id}/submit")
async def submit_test(request):
    lesson_id = int(request.match_info["lesson_id"])
    lesson = next((l for l in MONTHLY_LESSONS if l["id"] == lesson_id), None)
    if not lesson:
        return web.json_response({"error": "Not found"}, status=404)
    data = await request.json()
    user_id = data.get("user_id")
    answers = data.get("answers", [])
    if not user_id:
        return web.json_response({"error": "No user_id"}, status=400)
    score = sum(1 for i, a in enumerate(answers) if i < len(lesson["tests"]) and a == lesson["tests"][i]["correct"])
    total = len(lesson["tests"])
    bytes_earned = score * 5
    student = await get_student(int(user_id))
    student_name = student["full_name"] if student else f"ID:{user_id}"
    key = f"{user_id}_{lesson_id}"
    pending_tests[key] = {
        "student_id": int(user_id),
        "student_name": student_name,
        "lesson_id": lesson_id,
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
    return web.json_response({
        "success": True,
        "score": score,
        "total": total,
        "bytes_earned": bytes_earned,
        "result_emoji": emoji,
        "pending_key": key,
    })


@routes.get("/api/pending_status/{key}")
async def check_pending(request):
    key = request.match_info["key"]
    if key in pending_tests:
        return web.json_response({"status": "pending"})
    return web.json_response({"status": "approved"})


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
