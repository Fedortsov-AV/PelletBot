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
from bot.constants.roles import ADMIN

@pytest.mark.asyncio
async def test_show_arrival_menu_with_access():
    # Мокируем сессию и данные пользователя
    mock_session = MagicMock()
    mock_user = MagicMock()
    mock_user.role = 'admin'  # Пример роли администратора

    # Мокируем запрос к базе данных
    mock_session.execute.return_value.scalars.return_value.first.return_value = mock_user

    # Мокируем сообщение от пользователя
    mock_message = MagicMock(spec=types.Message)  # Используем спецификацию для правильного мокирования
    mock_message.from_user = MagicMock(id=12345)  # Мокируем from_user на объект с id 12345

    # Вызываем хэндлер
    await show_arrival_menu(mock_message, mock_session)

    # Проверяем, что был отправлен правильный ответ
    mock_message.answer.assert_called_once_with(
        "Выберите действие:",
        reply_markup=arrival_main_keyboard('ADMIN')  # Проверяем, что передан правильный объект клавиатуры
    )



@pytest.mark.asyncio
async def test_show_arrival_menu_without_access():
    # Мокируем сессию и данные пользователя
    mock_session = MagicMock()
    mock_user = MagicMock()
    mock_user.role = 'ANONYMOUS'  # Пример роли анонимного пользователя

    # Мокируем запрос к базе данных
    mock_session.execute.return_value.scalars.return_value.first.return_value = mock_user

    # Мокируем сообщение от пользователя
    mock_message = MagicMock()
    mock_message.from_user.id = 12345

    # Вызываем хэндлер
    await show_arrival_menu(mock_message, mock_session)

    # Проверяем, что отправляется сообщение об отсутствии доступа
    mock_message.answer.assert_called_once_with("❌ У вас нет доступа к функции 'Приходы'.")


@pytest.mark.asyncio
async def test_show_arrival_menu_user_not_found():
    # Мокируем сессию
    mock_session = MagicMock()

    # Мокируем запрос к базе данных, чтобы не найти пользователя
    mock_session.execute.return_value.scalars.return_value.first.return_value = None

    # Мокируем сообщение от пользователя
    mock_message = MagicMock()
    mock_message.from_user.id = 12345

    # Вызываем хэндлер
    await show_arrival_menu(mock_message, mock_session)

    # Проверяем, что отправляется сообщение об отсутствии доступа
    mock_message.answer.assert_called_once_with("❌ У вас нет доступа к функции 'Приходы'.")

@pytest.mark.asyncio
@patch('bot.handlers.arrival.get_user')
async def test_add_arrival_handler(mock_get_user, mock_callback, mock_state, mock_db_session, mock_user):
    from bot.handlers.arrival import add_arrival_handler

    mock_get_user.return_value = mock_user
    mock_callback.data = "add_arrival"

    await add_arrival_handler(mock_callback, mock_state, mock_db_session)

    mock_callback.message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_confirm_arrival(mock_callback, mock_state, mock_db_session):
    from bot.handlers.arrival import confirm_arrival

    # Мокируем цепочку вызовов для add_arrival
    mock_arrival = MagicMock()
    mock_arrival.id = 1
    mock_db_session.add = AsyncMock()
    mock_db_session.commit = AsyncMock()

    mock_callback.data = "arrival_confirm"
    mock_state.get_data.return_value = {"type": "Пеллеты ф 6мм", "amount": 10}

    await confirm_arrival(mock_callback, mock_state, mock_db_session)

    mock_callback.message.edit_text.assert_called()

# Аналогичные исправления для остальных тестов