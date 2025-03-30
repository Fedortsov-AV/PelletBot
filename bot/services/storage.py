from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from bot.models import Storage

async def get_stock(session: AsyncSession):
    result = await session.execute(select(Storage))
    stock = result.scalar_one_or_none()
    if not stock:
        stock = Storage()
        session.add(stock)
        await session.commit()
    return stock

# ➕ Обновить приход пеллет
async def update_stock_arrival(session: AsyncSession, amount: int):
    stock = await get_stock(session)
    stock.pellets_6mm += amount
    await session.commit()

# ➖ Обновить после фасовки
async def update_stock_packaging(session: AsyncSession, used_pellets: int, small_packs: int, large_packs: int):
    stock = await get_stock(session)
    stock.pellets_6mm -= used_pellets
    stock.packs_3kg += small_packs
    stock.packs_5kg += large_packs
    await session.commit()