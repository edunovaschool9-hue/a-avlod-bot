import os
import asyncpg
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
DEFAULT_BALANCE = 0

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return _pool

def serialize_row(row):
    """Convert asyncpg Record to dict, converting datetime to string"""
    if row is None:
        return None
    result = {}
    for key, value in dict(row).items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                telegram_id BIGINT PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                bytes_balance INTEGER DEFAULT 0,
                som_balance INTEGER DEFAULT 0,
                calf_kg REAL DEFAULT 40.0,
                level INTEGER DEFAULT 1,
                rank TEXT DEFAULT 'Junior',
                streak_days INTEGER DEFAULT 0,
                warnings INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT NOW(),
                last_active TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bytes_transactions (
                id SERIAL PRIMARY KEY,
                student_id BIGINT NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS som_transactions (
                id SERIAL PRIMARY KEY,
                student_id BIGINT NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS homeworks (
                id SERIAL PRIMARY KEY,
                student_id BIGINT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                reward_bytes INTEGER DEFAULT 0,
                status TEXT DEFAULT 'new',
                deadline TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                submitted_at TIMESTAMP,
                photo_file_id TEXT
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS lesson_access (
                id SERIAL PRIMARY KEY,
                student_id BIGINT NOT NULL,
                lesson_id INTEGER NOT NULL,
                unlocked_at TIMESTAMP DEFAULT NOW(),
                test_passed INTEGER DEFAULT 0,
                test_score INTEGER DEFAULT 0,
                UNIQUE(student_id, lesson_id)
            )
        """)

async def register_student(telegram_id, username, full_name):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT telegram_id FROM students WHERE telegram_id = $1", telegram_id
        )
        if existing:
            await conn.execute(
                "UPDATE students SET last_active = $1 WHERE telegram_id = $2",
                datetime.now(), telegram_id
            )
            return False
        await conn.execute("""
            INSERT INTO students (telegram_id, username, full_name, bytes_balance, som_balance, is_active)
            VALUES ($1, $2, $3, $4, $5, 0)
        """, telegram_id, username, full_name, DEFAULT_BALANCE, 0)
        return True

async def activate_student(telegram_id, som_amount):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE students SET is_active = 1, som_balance = $1 WHERE telegram_id = $2
        """, som_amount, telegram_id)
        await conn.execute("""
            INSERT INTO lesson_access (student_id, lesson_id)
            VALUES ($1, 1)
            ON CONFLICT (student_id, lesson_id) DO NOTHING
        """, telegram_id)
        await conn.execute("""
            INSERT INTO som_transactions (student_id, amount, reason)
            VALUES ($1, $2, $3)
        """, telegram_id, som_amount, "Kurs to'lovi")
    return True

async def get_student(telegram_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM students WHERE telegram_id = $1", telegram_id
        )
        return serialize_row(row)

async def get_student_by_username(username):
    username = username.lstrip('@')
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM students WHERE username = $1", username
        )
        return serialize_row(row)

async def find_student_by_username(username):
    return await get_student_by_username(username)

async def get_all_students():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM students ORDER BY bytes_balance DESC"
        )
        return [serialize_row(row) for row in rows]

async def add_bytes(student_id, amount, reason=""):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT bytes_balance FROM students WHERE telegram_id = $1", student_id
        )
        if not row:
            return False
        new_balance = row['bytes_balance'] + amount
        if new_balance < 0:
            return False
        await conn.execute(
            "UPDATE students SET bytes_balance = $1 WHERE telegram_id = $2",
            new_balance, student_id
        )
        await conn.execute(
            "INSERT INTO bytes_transactions (student_id, amount, reason) VALUES ($1, $2, $3)",
            student_id, amount, reason
        )
        return True

async def add_som(student_id, amount, reason=""):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT som_balance FROM students WHERE telegram_id = $1", student_id
        )
        if not row:
            return False
        new_balance = max(0, row['som_balance'] + amount)
        await conn.execute(
            "UPDATE students SET som_balance = $1 WHERE telegram_id = $2",
            new_balance, student_id
        )
        await conn.execute(
            "INSERT INTO som_transactions (student_id, amount, reason) VALUES ($1, $2, $3)",
            student_id, amount, reason
        )
        return True

async def update_calf(student_id, kg_change):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT calf_kg FROM students WHERE telegram_id = $1", student_id
        )
        if not row:
            return False
        new_kg = max(20.0, row['calf_kg'] + kg_change)
        await conn.execute(
            "UPDATE students SET calf_kg = $1 WHERE telegram_id = $2",
            new_kg, student_id
        )
        return True

async def get_transactions(student_id, limit=10):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM bytes_transactions
            WHERE student_id = $1
            ORDER BY created_at DESC LIMIT $2
        """, student_id, limit)
        return [serialize_row(row) for row in rows]

async def get_student_homeworks(student_id, status=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM homeworks WHERE student_id = $1 AND status = $2 ORDER BY created_at DESC",
                student_id, status
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM homeworks WHERE student_id = $1 ORDER BY created_at DESC",
                student_id
            )
        return [serialize_row(row) for row in rows]

async def submit_homework(homework_id, photo_file_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE homeworks SET status = 'review', photo_file_id = $1, submitted_at = $2 WHERE id = $3",
            photo_file_id, datetime.now(), homework_id
        )
        return True

async def create_homework(student_id, title, description, reward_bytes, deadline=None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO homeworks (student_id, title, description, reward_bytes, deadline)
            VALUES ($1, $2, $3, $4, $5) RETURNING id
        """, student_id, title, description, reward_bytes, deadline)
        return row['id']

async def get_lesson_access(student_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM lesson_access WHERE student_id = $1", student_id
        )
        return [serialize_row(row) for row in rows]

async def unlock_next_lesson(student_id, current_lesson_id):
    next_id = current_lesson_id + 1
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO lesson_access (student_id, lesson_id)
            VALUES ($1, $2)
            ON CONFLICT (student_id, lesson_id) DO NOTHING
        """, student_id, next_id)
        await conn.execute("""
            UPDATE lesson_access SET test_passed = 1
            WHERE student_id = $1 AND lesson_id = $2
        """, student_id, current_lesson_id)
    return True

async def add_warning(student_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT warnings FROM students WHERE telegram_id = $1", student_id
        )
        if not row:
            return 0
        warnings = row['warnings'] + 1
        await conn.execute(
            "UPDATE students SET warnings = $1 WHERE telegram_id = $2",
            warnings, student_id
        )
        return warnings

async def update_student_name(telegram_id, full_name):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE students SET full_name = $1 WHERE telegram_id = $2",
            full_name, telegram_id
        )
    return True
