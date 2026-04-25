from datetime import datetime

from sqlalchemy import select, extract
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.arrival import Arrival
from bot.models.rawProduct import RawProduct
from bot.services.storage import update_stock_arrival
from bot.services.user_service import get_user


async def get_raw_products(session: AsyncSession) -> list[RawProduct]:
    """Получить список всего сырья (id, name)."""
    result = await session.execute(select(RawProduct))
    return result.scalars().all()


async def get_raw_product_names(session: AsyncSession):
    """Оставлена для возможной обратной совместимости."""
    result = await session.execute(select(RawProduct.name))
    return [row[0] for row in result.all()]


async def add_arrival(session: AsyncSession, tg_id: int, raw_product_id: int, amount: int):
    """Добавление прихода с ID сырья."""
    try:
        user = await get_user(session, tg_id)
        arrival = Arrival(
            raw_product_id=raw_product_id,
            amount=amount,
            user_id=user.id,
            date=datetime.utcnow()
        )
        session.add(arrival)
        await session.flush()

        await update_stock_arrival(session, raw_product_id, amount)
        await session.commit()
        return arrival
    except SQLAlchemyError:
        await session.rollback()
        raise


# async def add_arrival(session: AsyncSession, tg_id: int, type: str, amount: int):
#     # Атомарная транзакция
#     try:
#         user = await get_user(session, tg_id)
#         # Добавляем приход
#         arrival = Arrival(
#             type=type,
#             amount=amount,
#             user_id=user.id,
#             date=datetime.utcnow(),
#         )
#         session.add(arrival)
#         await session.flush()
#
#         # Вызов обновления склада с передачей всех аргументов
#         await update_stock_arrival(session, type, amount)
#         await session.commit()
#         return arrival
#     except SQLAlchemyError:
#         await session.rollback()
#         raise


async def get_arrival_by_id(session: AsyncSession, id: int) -> Arrival | None:
    """
    Получает запись из таблицы Arrival по заданному id.
    """
    result = await session.execute(select(Arrival).filter(Arrival.id == id))
    return result.scalar_one_or_none()  # Вернет объект Arrival или None, если записи нет


async def get_arrivals_for_month(session: AsyncSession, user_id: int):
    """Получение приходов за текущий месяц"""
    current_month = datetime.utcnow().month
    result = await session.execute(
        select(Arrival).filter(
            extract('month', Arrival.date) == current_month,  # Используем extract для получения месяца

        )
    )
    return result.scalars().all()


async def delete_arrival(session: AsyncSession, arrival_id: int):
    """Удаление прихода с корректировкой склада."""
    print("=== SERVICE DELETE CALLED ===")
    arrival = await session.get(Arrival, arrival_id)
    if arrival:
        print(
            f"DEBUG DELETE: arrival_id={arrival_id}, raw_product_id={arrival.raw_product_id}, delta={-arrival.amount}")
        delta = -arrival.amount
        await update_stock_arrival(session, arrival.raw_product_id, delta)
        await session.delete(arrival)
        await session.commit()
    return arrival


async def update_arrival_amount(session: AsyncSession, arrival_id: int, new_amount: int):
    """Изменение количества прихода. Тип сырья не меняется."""
    try:
        arrival = await session.get(Arrival, arrival_id)
        if not arrival:
            return None
        delta = new_amount - arrival.amount
        arrival.amount = new_amount
        await update_stock_arrival(session, arrival.raw_product_id, delta)
        await session.commit()
        return arrival
    except SQLAlchemyError:
        await session.rollback()
        raise


async def get_raw_product_names(session: AsyncSession):
    """Получить список всех наименований raw_products из БД"""
    result = await session.execute(select(RawProduct.name))
    rows = result.all()  # Результат выполнения запроса
    # print(f"Rows: {rows}")  # Печать всех строк для отладки

    # Возвращаем список только с названиями продуктов
    return [row[0] for row in rows]
