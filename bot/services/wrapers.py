from functools import wraps
from aiogram import types
from aiogram.dispatcher.event.bases import CancelHandler

from cachetools import TTLCache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from bot.models.user import User

# Кеш для хранения ролей пользователей (актуальность 5 минут)
role_cache = TTLCache(maxsize=1000, ttl=300)


def extract_user(update: types.Update) -> types.User:
    """Извлекает пользователя из разных типов апдейтов"""
    if isinstance(update, types.Message):
        return update.from_user
    elif isinstance(update, types.CallbackQuery):
        return update.from_user
    raise CancelHandler()


async def get_or_create_user(session: AsyncSession, telegram_id: int, full_name: str) -> User:
    """Получает или создает пользователя в БД"""
    # Проверяем кеш
    if telegram_id in role_cache:
        return role_cache[telegram_id]

    # Ищем пользователя в БД
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()

    if not user:
        # Создаем нового пользователя
        user = User(telegram_id=telegram_id, full_name=full_name, role="anonymous")
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # Обновляем кеш
    role_cache[telegram_id] = user
    return user


def admin_required(func):
    """Только для администраторов"""

    @wraps(func)
    async def wrapper(update: types.Update, *args, **kwargs):
        from_user = extract_user(update)
        session: AsyncSession = kwargs.get('session')

        if not session:
            raise RuntimeError("Сессия БД не передана в аргументах")

        user = await get_or_create_user(session, from_user.id, from_user.full_name)

        if user.role != "admin":
            if isinstance(update, types.CallbackQuery):
                await update.answer("🔐 Доступ закрыт! Только для администраторов.", show_alert=True)
            else:
                await update.answer("🔐 Доступ закрыт! Только для администраторов.")
            raise CancelHandler()

        return await func(update, *args, **kwargs)

    return wrapper


def staff_required(func):
    """Для администраторов, менеджеров и операторов"""

    @wraps(func)
    async def wrapper(update: types.Update, *args, **kwargs):
        from_user = extract_user(update)
        session: AsyncSession = kwargs.get('session')

        if not session:
            raise RuntimeError("Сессия БД не передана в аргументах")

        user = await get_or_create_user(session, from_user.id, from_user.full_name)

        if user.role not in ("admin", "manager"):
            message = "👮‍♂️ Недостаточно прав! Доступно для: администраторов, менеджеров и операторов."
            if isinstance(update, types.CallbackQuery):
                await update.answer(message, show_alert=True)
            else:
                await update.answer(message)
            raise CancelHandler()

        return await func(update, *args, **kwargs)

    return wrapper


def restrict_anonymous(func):
    """Блокирует анонимных пользователей"""

    @wraps(func)
    async def wrapper(update: types.Update, *args, **kwargs):
        from_user = extract_user(update)
        session: AsyncSession = kwargs.get('session')

        if not session:
            raise RuntimeError("Сессия БД не передана в аргументах")

        # Быстрая проверка на анонимность без запроса к БД
        if getattr(from_user, 'is_anonymous', False):
            await update.answer("👻 Анонимы не проходят! Ваш ID сохранен. Обратитесь к администратору.")
            raise CancelHandler()

        user = await get_or_create_user(session, from_user.id, from_user.full_name)

        if user.role == "anonymous":
            await update.answer("❌ Ваш аккаунт не верифицирован. Обратитесь к администратору.")
            raise CancelHandler()

        return await func(update, *args, **kwargs)

    return wrapper