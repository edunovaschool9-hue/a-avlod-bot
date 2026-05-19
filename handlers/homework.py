from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.photo)
async def homework_handler(message: Message):

    text = """
📸 Uy vazifangiz qabul qilindi!

✅ O'qituvchi tekshiruviga yuborildi.
⭐ Tekshiruvdan keyin sizga baytlar beriladi.

Omad 🚀
"""

    await message.answer(text)
