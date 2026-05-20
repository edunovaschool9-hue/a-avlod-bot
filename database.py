import aiosqlite
from datetime import datetime
from config import DATABASE_PATH, DEFAULT_BALANCE


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                telegram_id INTEGER PRIMARY KEY,
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
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bytes_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(telegram_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS som_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(telegram_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS homeworks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                reward_bytes INTEGER DEFAULT 0,
                status TEXT DEFAULT 'new',
                deadline TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                submitted_at TIMESTAMP,
                photo_file_id TEXT,
                FOREIGN KEY (student_id) REFERENCES students(telegram_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS lesson_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                test_passed INTEGER DEFAULT 0,
                test_score INTEGER DEFAULT 0,
                UNIQUE(student_id, lesson_id),
                FOREIGN KEY (student_id) REFERENCES students(telegram_id)
            )
        """)
        await db.commit()


async def register_student(telegram_id, username, full_name):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT telegram_id FROM students WHERE telegram_id = ?", (telegram_id,))
        existing = await cursor.fetchone()
        if existing:
            await db.execute("UPDATE students SET last_active = ? WHERE telegram_id = ?", (datetime.now(), telegram_id))
            await db.commit()
            return False
        await db.execute("""
            INSERT INTO students (telegram_id, username, full_name, bytes_balance, som_balance, is_active)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (telegram_id, username, full_name, DEFAULT_BALANCE, 0))
        await db.commit()
        return True


async def activate_student(telegram_id, som_amount):
    """Activate student with initial som balance. Called by teacher."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE students SET is_active = 1, som_balance = ? WHERE telegram_id = ?
        """, (som_amount, telegram_id))
        await db.execute("""
            INSERT OR IGNORE INTO lesson_access (student_id, lesson_id) VALUES (?, 1)
        """, (telegram_id,))
        await db.execute("""
            INSERT INTO som_transactions (student_id, amount, reason) VALUES (?, ?, ?)
        """, (telegram_id, som_amount, "Kurs to'lovi"))
        await db.commit()
        return True


async def get_student(telegram_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM students WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_student_by_username(username):
    username = username.lstrip('@')
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM students WHERE username = ?", (username,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_students():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM students ORDER BY bytes_balance DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def add_bytes(student_id, amount, reason=""):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT bytes_balance FROM students WHERE telegram_id = ?", (student_id,))
        row = await cursor.fetchone()
        if not row:
            return False
        new_balance = row[0] + amount
        if new_balance < 0:
            return False
        await db.execute("UPDATE students SET bytes_balance = ? WHERE telegram_id = ?", (new_balance, student_id))
        await db.execute("INSERT INTO bytes_transactions (student_id, amount, reason) VALUES (?, ?, ?)", (student_id, amount, reason))
        await db.commit()
        return True


async def add_som(student_id, amount, reason=""):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT som_balance FROM students WHERE telegram_id = ?", (student_id,))
        row = await cursor.fetchone()
        if not row:
            return False
        new_balance = row[0] + amount
        if new_balance < 0:
            new_balance = 0
        await db.execute("UPDATE students SET som_balance = ? WHERE telegram_id = ?", (new_balance, student_id))
        await db.execute("INSERT INTO som_transactions (student_id, amount, reason) VALUES (?, ?, ?)", (student_id, amount, reason))
        await db.commit()
        return True


async def update_calf(student_id, kg_change):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT calf_kg FROM students WHERE telegram_id = ?", (student_id,))
        row = await cursor.fetchone()
        if not row:
            return False
        new_kg = max(20.0, row[0] + kg_change)
        await db.execute("UPDATE students SET calf_kg = ? WHERE telegram_id = ?", (new_kg, student_id))
        await db.commit()
        return True


async def get_transactions(student_id, limit=10):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM bytes_transactions WHERE student_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (student_id, limit))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_student_homeworks(student_id, status=None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute("SELECT * FROM homeworks WHERE student_id = ? AND status = ? ORDER BY created_at DESC", (student_id, status))
        else:
            cursor = await db.execute("SELECT * FROM homeworks WHERE student_id = ? ORDER BY created_at DESC", (student_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def submit_homework(homework_id, photo_file_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE homeworks SET status = 'review', photo_file_id = ?, submitted_at = ? WHERE id = ?", (photo_file_id, datetime.now(), homework_id))
        await db.commit()
        return True


async def create_homework(student_id, title, description, reward_bytes, deadline=None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO homeworks (student_id, title, description, reward_bytes, deadline)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, title, description, reward_bytes, deadline))
        await db.commit()
        return cursor.lastrowid


async def find_student_by_username(username):
    return await get_student_by_username(username)


async def get_lesson_access(student_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM lesson_access WHERE student_id = ?", (student_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def unlock_next_lesson(student_id, current_lesson_id):
    next_id = current_lesson_id + 1
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO lesson_access (student_id, lesson_id) VALUES (?, ?)
        """, (student_id, next_id))
        await db.execute("""
            UPDATE lesson_access SET test_passed = 1 WHERE student_id = ? AND lesson_id = ?
        """, (student_id, current_lesson_id))
        await db.commit()
        return True


async def add_warning(student_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT warnings FROM students WHERE telegram_id = ?", (student_id,))
        row = await cursor.fetchone()
        if not row:
            return 0
        warnings = row[0] + 1
        await db.execute("UPDATE students SET warnings = ? WHERE telegram_id = ?", (warnings, student_id))
        await db.commit()
        return warnings
