"""
API server for Telegram Mini App.
Mini App uses this to get and send data.
"""

import hmac
import hashlib
import json
from urllib.parse import parse_qs

from aiohttp import web

from database import (
    get_student,
    get_transactions,
    get_student_homeworks,
)

from config import BOT_TOKEN


routes = web.RouteTableDef()


def verify_telegram_data(init_data: str) -> dict | None:
    """
    Verifies Telegram Mini App data.
    """

    try:
        parsed = parse_qs(init_data)

        data_check_string_parts = []
        params = {}

        for key, values in parsed.items():
            if key != "hash":
                params[key] = values[0]
                data_check_string_parts.append(
                    f"{key}={values[0]}"
                )

        data_check_string = "\n".join(
            sorted(data_check_string_parts)
        )

        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        received_hash = parsed.get("hash", [""])[0]

        if computed_hash != received_hash:
            return None

        user_data = json.loads(
            params.get("user", "{}")
        )

        return user_data

    except Exception:
        return None


@routes.get("/")
async def index(request):
    """
    Main Mini App page
    """

    return web.FileResponse(
        "static/index.html"
    )


@routes.get("/api/profile")
async def get_profile(request):
    """
    Returns student profile data
    """

    init_data = request.headers.get(
        "X-Telegram-Init-Data",
        ""
    )

    user_id = request.rel_url.query.get(
        "user_id"
    )

    if init_data:
        user = verify_telegram_data(
            init_data
        )

        if not user:
            return web.json_response(
                {"error": "Unauthorized"},
                status=401
            )

        user_id = user.get("id")

    elif not user_id:
        return web.json_response(
            {"error": "No auth"},
            status=401
        )

    student = await get_student(
        int(user_id)
    )

    if not student:
        return web.json_response(
            {"error": "Not registered"},
            status=404
        )

    transactions = await get_transactions(
        int(user_id),
        limit=1000
    )

    total_earned = sum(
        t["amount"]
        for t in transactions
        if t["amount"] > 0
    )

    homeworks = await get_student_homeworks(
        int(user_id)
    )

    return web.json_response({
        "id": student["telegram_id"],
        "full_name": student["full_name"],
        "username": student["username"],
        "bytes_balance": student["bytes_balance"],
        "level": student["level"],
        "rank": student["rank"],
        "streak_days": student["streak_days"],
        "total_earned": total_earned,
        "homeworks_done": len([
            h for h in homeworks
            if h["status"] == "done"
        ]),
        "homeworks_active": len([
            h for h in homeworks
            if h["status"] == "new"
        ]),
    })


@routes.get("/api/homeworks")
async def get_homeworks(request):
    """
    Returns student homeworks
    """

    user_id = request.rel_url.query.get(
        "user_id"
    )

    if not user_id:
        return web.json_response(
            {"error": "No user_id"},
            status=400
        )

    homeworks = await get_student_homeworks(
        int(user_id)
    )

    return web.json_response({
        "homeworks": homeworks
    })


@routes.get("/api/transactions")
async def get_transactions_api(request):
    """
    Returns transactions
    """

    user_id = request.rel_url.query.get(
        "user_id"
    )

    if not user_id:
        return web.json_response(
            {"error": "No user_id"},
            status=400
        )

    transactions = await get_transactions(
        int(user_id),
        limit=20
    )

    return web.json_response({
        "transactions": transactions
    })


def create_app():
    """
    Create aiohttp app
    """

    app = web.Application()

    app.add_routes(routes)

    app.router.add_static(
        "/static",
        "static"
    )

    return app
