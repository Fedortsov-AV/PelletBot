from aiogram.types import Message
from sqlalchemy import select, extract
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import Storage
from bot.models.database import async_session
from bot.models.arrival import Arrival
from datetime import datetime

from bot.models.rawProduct import RawProduct


async def process_arrival(message: Message):
    """Обработка прихода без запроса комментария."""
    async with async_session() as session:
        arrival = Arrival(
            type="default",  # Можно заменить на реальный тип, если он есть
            amount=1,  # Можно передавать реальное количество
            date=datetime.utcnow(),
            user_id=message.from_user.id
        )
        session.add(arrival)
        await session.commit()

    await message.answer("Приход успешно зарегистрирован!")


async def add_arrival(session: AsyncSession, user_id: int, amount: int):
    async with session.begin():  # Атомарная транзакция
        try:
            # Добавляем приход
            arrival = Arrival(user_id=user_id, amount=amount, type="Пеллеты 6мм")
            session.add(arrival)

            # Обновляем склад
            stock = await session.execute(select(Storage))
            stock = stock.scalar_one_or_none()
            if not stock:
                stock = Storage(pellets_6mm=0, packs_3kg=0, packs_5kg=0)
                session.add(stock)

            stock.pellets_6mm += amount
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise

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
    """Удаление прихода по ID"""
    result = await session.execute(select(Arrival).where(Arrival.id == arrival_id))
    arrival = result.scalars().first()
    if arrival:
        await session.delete(arrival)
        await session.commit()
    return arrival

async def update_arrival_amount(session: AsyncSession, arrival_id: int, new_amount: int):
    """Изменение количества продукции в приходе"""
    result = await session.execute(select(Arrival).where(Arrival.id == arrival_id))
    arrival = result.scalars().first()
    if arrival:
        arrival.amount = new_amount
        await session.commit()
    return arrival

async def get_raw_product_names(session: AsyncSession):
    """Получить список всех наименований raw_products из БД"""
    result = await session.execute(select(RawProduct.name))
    return [row[0] for row in result.all()]