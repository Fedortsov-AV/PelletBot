import os
import sys

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.models.base import Base
from bot.middlewares.db import DBMiddleware


# --------------------------
# Настройка тестовой БД
# --------------------------

@pytest.fixture(scope="session")
def event_loop():
    """Фикстура для создания event loop"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_engine():
    """Движок для тестовой БД (в памяти)"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
def session_factory(async_engine):
    """Фабрика сессий для тестов (аналог вашей async_session)"""
    return async_sessionmaker(
        async_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )


@pytest.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """Сессия БД с автоматическим откатом"""
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


# --------------------------
# Фикстуры для тестирования aiogram
# --------------------------

@pytest.fixture
async def bot():
    """Тестовый экземпляр бота"""
    return Bot(token="test:token")


@pytest.fixture
async def dispatcher(session_factory):
    """Диспетчер с настроенным DBMiddleware"""
    dp = Dispatcher()

    # Инициализируем ваш middleware с session_factory
    dp.update.outer_middleware(DBMiddleware(session_factory))

    yield dp

    await dp.storage.close()


@pytest.fixture
def fake_user():
    """Фейковый пользователь Telegram"""
    return types.User(
        id=123,
        is_bot=False,
        first_name="Test",
        username="test_user"
    )


@pytest.fixture
def fake_chat():
    """Фейковый чат"""
    return types.Chat(
        id=1,
        type="private"
    )


@pytest.fixture
def fake_message(fake_user, fake_chat):
    """Фейковое сообщение"""
    return types.Message(
        message_id=1,
        date=None,
        chat=fake_chat,
        from_user=fake_user,
        text="/start"
    )


@pytest.fixture
def fake_update(fake_message):
    """Фейковое обновление"""
    return types.Update(
        update_id=1,
        message=fake_message
    )


@pytest.fixture
def fake_callback_query(fake_user, fake_chat):
    """Фейковый callback query"""
    return types.CallbackQuery(
        id="test_callback",
        from_user=fake_user,
        chat_instance="test",
        message=types.Message(
            message_id=1,
            date=None,
            chat=fake_chat,
            from_user=fake_user
        )
    )


# --------------------------
# Утилиты для тестирования
# --------------------------

@pytest.fixture
async def execute_handler(dispatcher, bot):
    """Утилита для выполнения хендлеров"""

    async def _execute_handler(handler, update, **kwargs):
        result = None

        async def wrapper(event, data):
            nonlocal result
            result = await handler(event, data)
            return result

        dispatcher.message.register(wrapper)
        await dispatcher.feed_update(bot, update)
        dispatcher.message.unregister(wrapper)

        return result

    return _execute_handler


# --------------------------
# Моки и патчи
# --------------------------

@pytest.fixture(autouse=True)
def mock_telegram_api():
    """Патчим вызовы к Telegram API"""
    with patch("aiogram.Bot.send_message"), \
            patch("aiogram.Bot.edit_message_text"), \
            patch("aiogram.Bot.delete_message"), \
            patch("aiogram.Bot.answer_callback_query"):
        yield

# --------------------------
# Моки для тестов хендлеров
# --------------------------

@pytest.fixture
def mock_message():
    """Фейковое сообщение с пользователем"""
    message = MagicMock()
    message.text = "/start"
    message.from_user = MagicMock()
    message.from_user.id = 1  # Устанавливаем ID пользователя
    message.from_user.username = "test_user"
    message.from_user.full_name = "Test User"
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    return message

@pytest.fixture
def mock_callback():
    """Фейковый callback с пользователем"""
    callback = MagicMock()
    callback.data = "test_callback"
    callback.from_user = MagicMock()
    callback.from_user.id = 1  # Устанавливаем ID пользователя
    callback.from_user.username = "test_user"
    callback.from_user.full_name = "Test User"
    callback.message = MagicMock()
    callback.message.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback

@pytest.fixture
def mock_state():
    state = AsyncMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.get_data = AsyncMock()
    state.clear = AsyncMock()
    return state

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_db_session_with_data(mock_db_session):
    """Мок сессии БД с поддержкой scalars()"""
    mock_result = MagicMock()
    mock_result.scalars = MagicMock()

    # Настройка поведения для scalars().first() и scalars().all()
    mock_result.scalars().first.return_value = MagicMock()
    mock_result.scalars().all.return_value = [MagicMock(), MagicMock()]

    mock_db_session.execute.return_value = mock_result
    return mock_db_session

@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    session = AsyncMock()

    # Мокируем цепочку вызовов SQLAlchemy
    mock_result = MagicMock()
    mock_result.scalars = MagicMock()
    mock_result.scalars().first = MagicMock()
    mock_result.scalars().all = MagicMock()
    mock_result.scalar_one_or_none = MagicMock()

    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    session.add = AsyncMock()

    return session

# --------------------------
# Тестовые данные
# --------------------------

@pytest.fixture
def test_user_data():
    return {
        "telegram_id": 123,
        "full_name": "Test User",
        "role": "admin",
    }


@pytest.fixture
def test_product_data():
    return {
        "article": "TEST123",
        "name": "Test Product",
        "quantity": 10
    }