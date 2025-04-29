import pytest
from aiogram.dispatcher.event.bases import CancelHandler

from bot.handlers.arrival import show_arrival_menu
from bot.keyboards.arrival import arrival_main_keyboard

import pytest
from bot.handlers.arrival import show_arrival_menu
from bot.keyboards.arrival import arrival_main_keyboard
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_show_arrival_menu_user_exists(fake_message, fake_user, mocker):
    # Создаем мок сессии
    session = AsyncMock()

    # Мокаем ответ от session.execute()
    execute_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.first.return_value = fake_user(1, 123, "test", "manager")
    execute_result.scalars.return_value = scalars_mock
    session.execute.return_value = execute_result

    # Мокаем функцию get_user (если нужно)
    mocker.patch("bot.handlers.arrival.get_user", return_value=fake_user(1, 123, "test", "manager"))

    # Вызываем хендлер
    await show_arrival_menu(fake_message, session=session)

@pytest.mark.asyncio
async def test_show_arrival_menu_user_not_exists(fake_message, mocker):
    session = AsyncMock()

    # Мокаем функцию get_user (пользователь не найден в кеше)
    mocker.patch("bot.handlers.arrival.get_user", return_value=None)

    # Мокаем session.execute так, чтобы пользователь в БД тоже не был найден
    execute_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.first.return_value = None
    execute_result.scalars.return_value = scalars_mock
    session.execute.return_value = execute_result

    # Ожидаем CancelHandler
    with pytest.raises(CancelHandler):
        await show_arrival_menu(fake_message, session=session)

    fake_message.answer.assert_called_once_with("❌ Ваш аккаунт не верифицирован. Обратитесь к администратору.")