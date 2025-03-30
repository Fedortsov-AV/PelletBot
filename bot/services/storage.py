from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from bot.models import Storage

# 🏭 Получить текущий склад (если нет — создать)
async def get_stock(session: AsyncSession):
    result = await session.execute(select(Storage).limit(1))
    stock = result.scalar_one_or_none()

    if not stock:
        stock = Storage()  # Создаём новую запись
        session.add(stock)
        await session.commit()
        await session.refresh(stock)  # Обновляем объект после коммита

    return stock

# ➕ Обновить приход пеллет (атомарно)
async def update_stock_arrival(session: AsyncSession, amount: int):
    """Обновление остатков на складе после прихода."""
    storage = await session.get(Storage, 1)

    if not storage:
        storage = Storage(pellets_6mm=amount)  # Создаём склад, если его ещё нет
        session.add(storage)
    else:
        storage.pellets_6mm += amount  # Обновляем количество

# ➖ Обновить после фасовки (атомарно)
async def update_stock_packaging(session: AsyncSession, used_pellets: int, small_packs: int, large_packs: int):
     # Гарантируем атомарность
    stock = await get_stock(session)

    # Проверка на недостаток пеллет перед фасовкой
    if stock.pellets_6mm < used_pellets:
        raise ValueError("Недостаточно пеллет на складе!")

    stock.pellets_6mm -= used_pellets
    stock.packs_3kg += small_packs
    stock.packs_5kg += large_packs

    await session.commit()