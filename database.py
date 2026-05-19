"""
Модуль работы с базой данных SQLite.
SQLite — это простая база данных в виде одного файла.
Идеально для старта, потом можно мигрировать на PostgreSQL.
"""

import aiosqlite
from datetime import datetime
from config import DATABASE_PATH, DEFAULT_BALANCE


async def init_db():
    """Создаёт таблицы при первом запуске бота."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Таблица учеников
        await db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                bytes_balance INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                rank TEXT DEFAULT 'Junior',
                streak_days INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # История начислений байтов
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

        # Таблица домашних заданий
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

        await db.commit()


async def register_student(telegram_id: int, username: str, full_name: str) -> bool:
    """
    Регистрирует нового ученика.
    Возвращает True если ученик новый, False если уже есть.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем есть ли уже такой ученик
        cursor = await db.execute(
            "SELECT telegram_id FROM students WHERE telegram_id = ?",
            (telegram_id,)
        )
        existing = await cursor.fetchone()

        if existing:
            # Обновляем last_active
            await db.execute(
                "UPDATE students SET last_active = ? WHERE telegram_id = ?",
                (datetime.now(), telegram_id)
            )
            await db.commit()
            return False

        # Создаём нового ученика
        await db.execute("""
            INSERT INTO students (telegram_id, username, full_name, bytes_balance)
            VALUES (?, ?, ?, ?)
        """, (telegram_id, username, full_name, DEFAULT_BALANCE))
        await db.commit()
        return True


async def get_student(telegram_id: int):
    """Получает данные ученика по его Telegram ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM students WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_students():
    """Получает список всех учеников (для учителя)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM students ORDER BY bytes_balance DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def add_bytes(student_id: int, amount: int, reason: str = "") -> bool:
    """
    Начисляет или списывает байты ученику.
    amount может быть отрицательным (списание).
    Возвращает True если успешно.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Проверяем что ученик существует
        cursor = await db.execute(
            "SELECT bytes_balance FROM students WHERE telegram_id = ?",
            (student_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return False

        current_balance = row[0]
        new_balance = current_balance + amount

        # Не даём уйти в минус
        if new_balance < 0:
            return False

        # Обновляем баланс
        await db.execute(
            "UPDATE students SET bytes_balance = ? WHERE telegram_id = ?",
            (new_balance, student_id)
        )

        # Записываем транзакцию в историю
        await db.execute("""
            INSERT INTO bytes_transactions (student_id, amount, reason)
            VALUES (?, ?, ?)
        """, (student_id, amount, reason))

        await db.commit()
        return True


async def get_transactions(student_id: int, limit: int = 10):
    """Получает последние транзакции ученика."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM bytes_transactions
            WHERE student_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (student_id, limit))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def find_student_by_username(username: str):
    """Ищет ученика по @username (без @)."""
    username = username.lstrip('@')
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM students WHERE username = ?",
            (username,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_homework(student_id: int, title: str, description: str,
                          reward_bytes: int, deadline=None) -> int:
    """Создаёт новое ДЗ для ученика. Возвращает ID созданного ДЗ."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO homeworks (student_id, title, description, reward_bytes, deadline)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, title, description, reward_bytes, deadline))
        await db.commit()
        return cursor.lastrowid


async def get_student_homeworks(student_id: int, status: str = None):
    """Получает ДЗ ученика. Можно фильтровать по статусу."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute("""
                SELECT * FROM homeworks
                WHERE student_id = ? AND status = ?
                ORDER BY created_at DESC
            """, (student_id, status))
        else:
            cursor = await db.execute("""
                SELECT * FROM homeworks
                WHERE student_id = ?
                ORDER BY created_at DESC
            """, (student_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def submit_homework(homework_id: int, photo_file_id: str) -> bool:
    """Ученик сдаёт ДЗ — отмечает как 'на проверке' и прикрепляет фото."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE homeworks
            SET status = 'review', photo_file_id = ?, submitted_at = ?
            WHERE id = ?
        """, (photo_file_id, datetime.now(), homework_id))
        await db.commit()
        return True
