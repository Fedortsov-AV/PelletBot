import os
import sys
from contextlib import asynccontextmanager

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from typing import AsyncGenerator

import pytest_asyncio
from aiogram.types import Message, CallbackQuery
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
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
def session_factory(async_engine):
    return async_sessionmaker(
        async_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

@asynccontextmanager
@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncSession:  # Правильная аннотация
    session = session_factory()
    try:
        yield session
    except Exception as e:
        print(e)
        await session.rollback()
    finally:
        await session.close()



# --------------------------
# Фикстуры для тестирования aiogram
# --------------------------

@pytest.fixture
async def bot():
    """Тестовый экземпляр бота"""
    return Bot(token="test:token")


@pytest_asyncio.fixture
async def dispatcher(session_factory) -> Dispatcher:
    """Диспетчер с настроенным DBMiddleware"""
    dp = Dispatcher()
    dp.update.outer_middleware(DBMiddleware(session_factory))
    await dp.emit_startup()  # Инициализация
    yield dp                 # Возвращаем объект Dispatcher
    await dp.emit_shutdown() # Завершение работы
    await dp.storage.close()

@pytest.fixture
def fake_user():
    """Фейковый пользователь Telegram"""
    return types.User(
        id=123,
        is_bot=False,
        first_name="Test",
        username="test_user",

    )


@pytest.fixture
def fake_chat():
    """Фейковый чат"""
    return types.Chat(
        id=1,
        type="private"
    )

@pytest.fixture
def fake_message(mocker):
    message = mocker.MagicMock(spec=Message)
    message.answer = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = 123
    message.from_user.is_anonymous = False
    return message

@pytest.fixture
def fake_update(fake_message):
    """Фейковое обновление"""
    return types.Update(
        update_id=1,
        message=fake_message
    )


@pytest.fixture
def fake_callback(mocker):
    cb = mocker.MagicMock(spec=CallbackQuery)
    cb.data = "arrival_type:pellets"
    cb.message = mocker.MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()

    # Явно добавляем from_user с нужными полями
    cb.from_user = mocker.MagicMock()
    cb.from_user.id = 123
    cb.from_user.full_name = "Test User"
    cb.from_user.is_anonymous = False

    return cb

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
def fake_user():
    class User:
        def __init__(self, id, telegram_id, fullname, role):
            self.id = id
            self.telegram_id = telegram_id
            self.fullname = fullname
            self.role = role
    return User



def mock_storage(mocker):
    """
    Фикстура для мокирования хранилища FSM (pytest-mock).
    Методы set_data и update_data замоканы как AsyncMock.
    """
    storage = mocker.MagicMock()
    # Мокаем асинхронные методы set_data и update_data для FSMContext
    storage.set_data = mocker.AsyncMock(return_value=None)
    storage.update_data = mocker.AsyncMock(return_value=None)
    return storage

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