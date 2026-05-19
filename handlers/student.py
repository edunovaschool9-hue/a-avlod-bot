from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "📚 Darslar")
async def lessons_handler(message: Message):

    text = """
📚 Mavjud darslar:

1️⃣ Bloging asoslari
2️⃣ Kontent yaratish
3️⃣ Sun'iy intellekt
4️⃣ Mobil video montaj
5️⃣ Soft skills

Yangi darslar tez orada qo'shiladi 🚀
"""

    await message.answer(text)


@router.message(F.text == "💰 Baytlarim")
async def bytes_handler(message: Message):

    text = """
💰 Sizning baytlaringiz:

⭐ 120 bayt

Baytlarni:
✅ Uy vazifa bajarish
✅ Dars ko'rish
✅ Faollik

orqali yig'ishingiz mumkin.
"""

    await message.answer(text)
