from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from bot.constants.roles import ADMIN, MANAGER, OPERATOR, ANONYMOUS
from bot.models.role import Role

async def get_all_roles(session: AsyncSession):
    """Получение всех ролей из базы данных."""
    result = await session.execute(select(Role))
    return result.scalars().all()

async def fill_roles(session: AsyncSession):
    """Заполняем таблицу ролей предустановленными значениями."""
    # Список ролей, которые мы хотим добавить в таблицу
    roles = [ADMIN, MANAGER, OPERATOR, ANONYMOUS]

    for role_name in roles:
        # Проверяем, есть ли уже такая роль
        existing_role = await session.execute(select(Role).filter_by(name=role_name))
        existing_role = existing_role.scalars().first()

        # Если роли нет, добавляем её
        if not existing_role:
            role = Role(name=role_name)
            session.add(role)
            await session.commit()
    return True