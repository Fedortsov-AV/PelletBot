from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from bot.config import ADMIN_IDS
from bot.constants.roles import ADMIN, ANONYMOUS
from bot.models.user import User

async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    """Получает пользователя из БД по Telegram ID."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalars().first()

async def create_user(session: AsyncSession, tg_user) -> User:
    """Создаёт нового пользователя с ролью 'anonymous'."""

    user = User(
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
        role=ANONYMOUS if tg_user.id not in ADMIN_IDS else ADMIN
    )
    session.add(user)
    await session.commit()
    return user