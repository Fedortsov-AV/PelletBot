from unittest.mock import AsyncMock, MagicMock, patch

import async_generator
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
async def test_show_arrival_menu_with_access(db_session: AsyncSession):  # Исправлено!
    user = User(
        telegram_id=123,
        full_name="Test User",
        role="manager"
    )
    print(f'!!!!!!!!!!!!{type(db_session)=}')
    sess = db_session.asend(None)
    print(f'!!!!!!!!!!!!{type(sess)=}')
    sios = sess.transaction()
    print(f'!!!!!!!!!!!!{type(sios)=}')
    with db_session.begin():
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

    message = AsyncMock(spec=Message)
    message.from_user.id = 123

    with patch("bot.handlers.arrival.get_user", new=AsyncMock(return_value=user)):
        await show_arrival_menu(message, session=db_session)

    message.answer.assert_awaited_once_with(
        "Выберите действие:",
        reply_markup=arrival_main_keyboard("manager")
    )