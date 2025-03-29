from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from bot.models.user import User

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    """Получает пользователя по Telegram ID"""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()

async def register_user(session: AsyncSession, telegram_id: int, full_name: str, role: str = "anonymous") -> User:
    """Регистрирует нового пользователя"""
    user = User(telegram_id=telegram_id, full_name=full_name, role=role)
    session.add(user)
    await session.commit()
    return user

async def get_user_role(session: AsyncSession, telegram_id: int) -> str:
    """Возвращает роль пользователя"""
    user = await get_user_by_telegram_id(session, telegram_id)
    return user.role if user else "anonymous"


async def update_user_role(session: AsyncSession, telegram_id: int, new_role: str) -> bool:
    """Обновляет роль пользователя"""
    user = await get_user_by_telegram_id(session, telegram_id)

    if not user:
        return False

    user.role = new_role
    await session.commit()
    return True

async def get_all_users(session: AsyncSession):
    """Возвращает список всех пользователей"""
    result = await session.execute(select(User))
    return result.scalars().all()