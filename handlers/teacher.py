from aiogram import Router
from aiogram.types import Message
from config import TEACHER_ID

router = Router()


@router.message(lambda message: message.from_user.id == int(TEACHER_ID))
async def teacher_panel(message: Message):

    text = """
👨‍🏫 O'qituvchi paneli

Siz quyidagilarni boshqarishingiz mumkin:

✅ Uy vazifalar
✅ O'quvchilar
✅ Bayt tizimi
✅ Statistikalar

Admin panel tez orada kengaytiriladi 🚀
"""

    await message.answer(text)
