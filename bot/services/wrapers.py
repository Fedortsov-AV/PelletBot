from datetime import datetime
from functools import wraps
from typing import Callable, Optional, Dict

from aiogram import types
from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from cachetools import TTLCache
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from bot.constants.roles import ANONYMOUS, ADMIN, MANAGER
from bot.context import app_context
from bot.models.user import User
from bot.services.db_service import DBService
import logging

logger = logging.getLogger(__name__)

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
        user = User(telegram_id=telegram_id, full_name=full_name, role=ANONYMOUS)
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

        if user.role != ADMIN:
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

        if user.role not in (ADMIN, MANAGER):
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
            # Пытаемся получить сессию из data (для callback)
            if 'data' in kwargs and hasattr(kwargs['data'], 'get'):
                session = kwargs['data'].get('session')

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


async def _fetch_entity_data(session: AsyncSession, entity_name: str, entity_id: int) -> Optional[Dict]:
    try:
        model = DBService.get_model(entity_name)
        if not model:
            logger.error(f"Model not found for entity: {entity_name}")
            return None
        entity = await session.get(model, entity_id)
        if entity:
            return {col.name: getattr(entity, col.name) for col in entity.__table__.columns}
        return None
    except Exception as e:
        logger.error(f"Error fetching entity data: {e}")
        return None


def track_changes(entity_name: str):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            session: Optional[AsyncSession] = None
            fsm_context: Optional[FSMContext] = None
            message: Optional[Message] = None
            callback: Optional[CallbackQuery] = None

            for arg in args:
                if isinstance(arg, AsyncSession):
                    session = arg
                elif isinstance(arg, FSMContext):
                    fsm_context = arg
                elif isinstance(arg, Message):
                    message = arg
                elif isinstance(arg, CallbackQuery):
                    callback = arg

            if not session:
                session = kwargs.get("session")

            if not session:
                logger.error("Session not found in track_changes")
                return await func(*args, **kwargs)

            telegram_id = None
            if message:
                telegram_id = message.from_user.id
            elif callback:
                telegram_id = callback.from_user.id
            else:
                telegram_id = kwargs.get("tg_id") or kwargs.get("telegram_id")

            user_id = None
            if telegram_id:
                result = await session.execute(select(User).where(User.telegram_id == telegram_id))
                user = result.scalars().first()
                if user:
                    user_id = user.id
                else:
                    logger.warning(f"User with telegram_id {telegram_id} not found")

            # === Определение ID сущности ===
            entity_id = None
            result = None
            old_data = None
            logger.info(f"func name: {func.__name__=}")
            if func.__name__.startswith(("update_", "delete_")):
                # 1. из kwargs
                entity_id = kwargs.get(f"{entity_name}_id") or kwargs.get("id")

                # 2. из FSM
                if not entity_id and fsm_context:
                    state_data = await fsm_context.get_data()
                    entity_id = state_data.get(f"{entity_name}_id") or state_data.get("id")

                # 3. из callback.data (например, "delete_arrival:52")
                print(f'!!!!!!!!!!!!!!!!!!!!{entity_id=}, {callback=}, {callback.data=}')
                if not entity_id and callback and callback.data:
                    parts = callback.data.split(":")
                    if len(parts) == 2:
                        try:
                            entity_id = int(parts[1])
                        except ValueError:
                            print(f'ValueError!!!!!!!!!!!!!!!!!!!!!!!')
                print(f'!!!!!!!!!!!!!!!!!!!!!!!!!!!{entity_id=}')
                if entity_id:
                    old_data = await _fetch_entity_data(session, entity_name, entity_id)

            # === Выполнение функции ===
            result = await func(*args, **kwargs)

            # === Получение new_data ===
            new_data = None
            if not func.__name__.startswith("delete_"):
                # 1. из результата
                entity_id = getattr(result, "id", None)

                # 2. из kwargs
                if not entity_id:
                    entity_id = kwargs.get(f"{entity_name}_id") or kwargs.get("id")

                # 3. из FSM
                if not entity_id and fsm_context:
                    state_data = await fsm_context.get_data()
                    entity_id = state_data.get(f"{entity_name}_id") or state_data.get("id")

                if not entity_id and callback and callback.data:
                    parts = callback.data.split(":")
                    if len(parts) == 2:
                        try:
                            entity_id = int(parts[1])
                        except ValueError:
                            print(f'ValueError!!!!!!!!!!!!!!!!!!!!!!!')

                if entity_id:
                    new_data = await _fetch_entity_data(session, entity_name, entity_id)

            logger.info(f"[track_changes] entity_id: {entity_id}")
            logger.info(f"[track_changes] old_data: {bool(old_data)} | new_data: {bool(new_data)}")

            if user_id and entity_id and (old_data or new_data):
                try:
                    user = await session.get(User, user_id)
                    if not user:
                        logger.error(f"User with ID {user_id} not found.")
                        return result

                    action = (
                        "create" if func.__name__.startswith(("add_", "create_", "confirm_")) else
                        "update" if func.__name__.startswith("update_") else
                        "delete"
                    )

                    message_text = _format_notification(
                        user=user,
                        action=action,
                        entity_name=entity_name,
                        entity_id=entity_id,
                        old_data=old_data,
                        new_data=new_data
                    )

                    await app_context.notification_service.send_notification(
                        session=session,
                        user_id=user_id,
                        message=message_text
                    )

                except Exception as e:
                    logger.error(f"Notification error: {e}", exc_info=True)

            return result

        return wrapper

    return decorator


def _format_notification(user: User, action: str, entity_name: str,
                         entity_id: int, old_data: Dict, new_data: Dict) -> str:
    """Форматирует текст уведомления"""
    lines = [
        f"👤 Пользователь: {user.full_name} (ID: {user.telegram_id})",
        f"⚡ Действие: {action} {entity_name}" + (f" #{entity_id}" if entity_id else ""),
        f"🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    ]

    if action == "update" and old_data and new_data:
        changes = [
            f"  - {field}: {old_data[field]} → {new_data[field]}"
            for field in new_data if field in old_data and old_data[field] != new_data[field]
        ]
        if changes:
            lines.append("📝 Изменения:")
            lines.extend(changes)
    elif action == "create" and new_data:
        lines.append("📌 Данные:")
        lines.extend(f"  - {k}: {v}" for k, v in new_data.items())
    elif action == "delete" and old_data:
        lines.append("🗑 Удалено:")
        lines.extend(f"  - {k}: {v}" for k, v in old_data.items())

    return "\n".join(lines)

async def get_entity_id(result, kwargs: dict, fsm_context: FSMContext | None, entity_name: str) -> int | None:
    # 1. Пробуем получить из результата выполнения функции
    if result and hasattr(result, "id"):
        return result.id

    # 2. Пробуем найти в kwargs по имени сущности
    entity_id = kwargs.get(f"{entity_name}_id") or kwargs.get("id")
    if entity_id:
        return entity_id

    # 3. Пробуем из FSMContext, если доступен
    if fsm_context:
        state_data = await fsm_context.get_data()
        return state_data.get(f"{entity_name}_id") or state_data.get("id")

    # 4. Ничего не нашли
    return None