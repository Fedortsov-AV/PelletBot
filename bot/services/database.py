from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from bot.models.user import User

async def get_or_create_user(session: AsyncSession, telegram_id: int, full_name: str):
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()

    if not user:
        user = User(telegram_id=telegram_id, full_name=full_name, role="anonymous")
        session.add(user)
        await session.commit()

    return user

async def update_user_role(session: AsyncSession, user_id: int, new_role: str):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if user:
        user.role = new_role
        await session.commit()