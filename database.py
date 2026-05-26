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
        try:
            await conn.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS reminder_count INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await conn.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS last_active TIMESTAMP")
        except Exception:
            pass

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                bytes_balance INTEGER DEFAULT 0,
                som_balance INTEGER DEFAULT 0,
                calf_kg FLOAT DEFAULT 40.0,
                is_active INTEGER DEFAULT 0,
                warnings INTEGER DEFAULT 0,
                reminder_count INTEGER DEFAULT 0,
                last_active TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
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
                UNIQUE(student_id, lesson_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tez_aytish_access (
                id SERIAL PRIMARY KEY,
                student_id BIGINT NOT NULL,
                lesson_id INTEGER NOT NULL,
                unlocked_at TIMESTAMP DEFAULT NOW(),
                status TEXT DEFAULT 'locked',
                UNIQUE(student_id, lesson_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tez_aytish_submissions (
                id SERIAL PRIMARY KEY,
                student_id BIGINT NOT NULL,
                lesson_id INTEGER NOT NULL,
                voice_file_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                submitted_at TIMESTAMP DEFAULT NOW(),
                reviewed_at TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id SERIAL PRIMARY KEY,
                student_id BIGINT NOT NULL,
                day_of_week INTEGER NOT NULL,
                lesson_time TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(student_id, day_of_week)
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

async def update_last_active(student_id):
    """Update last_active timestamp when student does any activity."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE students SET last_active = NOW() WHERE telegram_id = $1",
            student_id
        )

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

async def get_student_homeworks(student_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
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

async def get_tez_aytish_access(student_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM tez_aytish_access WHERE student_id = $1 ORDER BY lesson_id",
            student_id
        )
        return [serialize_row(row) for row in rows]

async def unlock_tez_aytish_lesson(student_id, lesson_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO tez_aytish_access (student_id, lesson_id, status)
            VALUES ($1, $2, 'open')
            ON CONFLICT (student_id, lesson_id) DO UPDATE SET status = 'open'
        """, student_id, lesson_id)
    return True

async def submit_tez_aytish_voice(student_id, lesson_id, voice_file_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM tez_aytish_submissions
            WHERE student_id = $1 AND lesson_id = $2 AND status = 'pending'
        """, student_id, lesson_id)
        row = await conn.fetchrow("""
            INSERT INTO tez_aytish_submissions (student_id, lesson_id, voice_file_id, status)
            VALUES ($1, $2, $3, 'pending') RETURNING id
        """, student_id, lesson_id, voice_file_id)
        await conn.execute("""
            UPDATE tez_aytish_access SET status = 'pending'
            WHERE student_id = $1 AND lesson_id = $2
        """, student_id, lesson_id)
    return row['id']

async def approve_tez_aytish(submission_id, student_id, lesson_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE tez_aytish_submissions SET status = 'approved', reviewed_at = NOW()
            WHERE id = $1
        """, submission_id)
        await conn.execute("""
            UPDATE tez_aytish_access SET status = 'done'
            WHERE student_id = $1 AND lesson_id = $2
        """, student_id, lesson_id)
        next_id = lesson_id + 1
        await conn.execute("""
            INSERT INTO tez_aytish_access (student_id, lesson_id, status)
            VALUES ($1, $2, 'open')
            ON CONFLICT (student_id, lesson_id) DO NOTHING
        """, student_id, next_id)
    return True

async def reject_tez_aytish(submission_id, student_id, lesson_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE tez_aytish_submissions SET status = 'rejected', reviewed_at = NOW()
            WHERE id = $1
        """, submission_id)
        await conn.execute("""
            UPDATE tez_aytish_access SET status = 'open'
            WHERE student_id = $1 AND lesson_id = $2
        """, student_id, lesson_id)
    return True

async def get_pending_tez_aytish():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT ts.*, s.full_name, s.username
            FROM tez_aytish_submissions ts
            JOIN students s ON s.telegram_id = ts.student_id
            WHERE ts.status = 'pending'
            ORDER BY ts.submitted_at
        """)
        return [serialize_row(row) for row in rows]

async def activate_tez_aytish_for_student(student_id):
    """Give student access to first tez aytish lesson"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO tez_aytish_access (student_id, lesson_id, status)
            VALUES ($1, 1, 'open')
            ON CONFLICT (student_id, lesson_id) DO NOTHING
        """, student_id)
    return True

async def activate_tez_aytish_for_all_active_students():
    """Activate tez aytish lesson 1 for ALL active students who don't have access yet.
    Called on bot startup to fix existing students automatically.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        students = await conn.fetch(
            "SELECT telegram_id FROM students WHERE is_active = 1"
        )
        count = 0
        for student in students:
            sid = student['telegram_id']
            result = await conn.execute("""
                INSERT INTO tez_aytish_access (student_id, lesson_id, status)
                VALUES ($1, 1, 'open')
                ON CONFLICT (student_id, lesson_id) DO NOTHING
            """, sid)
            if result == "INSERT 0 1":
                count += 1
    return count

async def set_student_schedule(student_id, day_of_week, lesson_time):
    """Set schedule for student. day_of_week: 0=Mon..6=Sun"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO schedules (student_id, day_of_week, lesson_time)
            VALUES ($1, $2, $3)
            ON CONFLICT (student_id, day_of_week) DO UPDATE SET lesson_time = $3
        """, student_id, day_of_week, lesson_time)
    return True

async def delete_student_schedule_day(student_id, day_of_week):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM schedules WHERE student_id = $1 AND day_of_week = $2",
            student_id, day_of_week
        )
    return True

async def delete_student_schedule(student_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM schedules WHERE student_id = $1", student_id)
    return True

async def get_student_schedule(student_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM schedules WHERE student_id = $1 ORDER BY day_of_week",
            student_id
        )
        return [serialize_row(row) for row in rows]

async def get_all_schedules():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT sc.*, s.full_name, s.username, s.telegram_id, s.calf_kg
            FROM schedules sc
            JOIN students s ON s.telegram_id = sc.student_id
            WHERE s.is_active = 1
            ORDER BY sc.day_of_week, sc.lesson_time
        """)
        return [serialize_row(row) for row in rows]

async def get_students_with_lesson_tomorrow(tomorrow_dow):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT sc.student_id, sc.lesson_time, s.full_name, s.username, s.calf_kg
            FROM schedules sc
            JOIN students s ON s.telegram_id = sc.student_id
            WHERE sc.day_of_week = $1 AND s.is_active = 1
        """, tomorrow_dow)
        return [serialize_row(row) for row in rows]

async def get_students_with_lesson_today(today_dow):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT sc.student_id, sc.lesson_time, sc.day_of_week,
                   s.full_name, s.username, s.calf_kg, s.telegram_id
            FROM schedules sc
            JOIN students s ON s.telegram_id = sc.student_id
            WHERE sc.day_of_week = $1 AND s.is_active = 1
        """, today_dow)
        return [serialize_row(row) for row in rows]

async def check_student_completed_tasks(student_id, lesson_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        test_row = await conn.fetchrow("""
            SELECT test_passed FROM lesson_access
            WHERE student_id = $1 AND lesson_id = $2
        """, student_id, lesson_id)
        tez_row = await conn.fetchrow("""
            SELECT status FROM tez_aytish_access
            WHERE student_id = $1 AND lesson_id = $2
        """, student_id, lesson_id)
        test_done = test_row and test_row['test_passed'] == 1
        tez_done = tez_row and tez_row['status'] in ('done', 'pending')
        return test_done, tez_done

async def get_current_lesson_for_student(student_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT MAX(lesson_id) as max_lesson FROM lesson_access
            WHERE student_id = $1
        """, student_id)
        return row['max_lesson'] if row else 1
