from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from bot.models.packaging import Packaging
from bot.models.arrival import Arrival


async def get_current_stock(session: AsyncSession):
    """Получаем остаток первичной продукции на складе"""
    result = await session.execute(select(Arrival))
    total_stock = sum(row.amount for row in result.scalars())
    return total_stock


async def save_packaging(session: AsyncSession, user_id: int, small_packs: int, large_packs: int, used_raw: int):
    """Сохраняем фасовку и обновляем складские остатки"""
    packaging = Packaging(
        small_packs=small_packs,
        large_packs=large_packs,
        used_raw_material=used_raw,
        user_id=user_id
    )
    session.add(packaging)

    # Уменьшаем количество первичной продукции
    result = await session.execute(select(Arrival).order_by(Arrival.date.asc()))
    arrivals = result.scalars().all()

    remaining = used_raw
    for arrival in arrivals:
        if remaining <= 0:
            break
        if arrival.amount >= remaining:
            arrival.amount -= remaining
            remaining = 0
        else:
            remaining -= arrival.amount
            arrival.amount = 0

    await session.commit()
