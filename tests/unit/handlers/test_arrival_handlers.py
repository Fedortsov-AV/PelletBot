from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.fsm.arrival import ArrivalState
from bot.handlers.arrival import show_arrival_menu
from bot.keyboards.arrival import arrival_main_keyboard
from bot.models import User
from bot.constants.roles import ADMIN, MANAGER
from bot.services.user_service import get_user


@pytest.mark.asyncio
async def test_show_arrival_menu_with_access(db_session: AsyncSession):
    # Создаем пользователя
    user_data = {"id": 1, "role": MANAGER, "full_name": "Test User", "telegram_id": 123}
    user = User(**user_data)

    # Получаем сессию из db_session через async with
    async with db_session as session:
        # Добавляем пользователя в БД внутри асинхронного контекста
        session.add(user)
        await session.commit()  # Является асинхронным методом для сохранения

    # Мокаем сообщение
    message = AsyncMock()
    message.from_user.id = 123

    # Патчим функцию get_user, чтобы вернуть нашего пользователя
    with patch("handlers.arrival.get_user", return_value=user):
        await show_arrival_menu(message, db_session)

    # Проверяем, что ответ отправился
    message.answer.assert_awaited_with(
        "Выберите действие:",
        reply_markup=arrival_main_keyboard(user.role)
    )
