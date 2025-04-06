from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.main import get_main_keyboard
from bot.services.user_service import get_user, create_user

router = Router()


@router.message(Command("start"))
async def start_handler(message: Message, session: AsyncSession):
    """Обработчик команды /start, проверяет пользователя в БД и отправляет нужную клавиатуру."""
    user = await get_user(session, message.from_user.id)

    if not user:  # Если пользователя нет в БД, создаём его с ролью "anonymous"
        user = await create_user(session, message.from_user)

    keyboard = get_main_keyboard(user.role)
    await message.answer("Выберите действие:", reply_markup=keyboard)
