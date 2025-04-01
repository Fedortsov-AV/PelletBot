from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, extract, case
from datetime import datetime, date
from typing import Dict, List, Union

from bot.models import (
    User,
    Arrival,
    Packaging,
    Expense,
    Product,
    RawMaterialStorage,
    ProductStorage,
    RawProduct, ShipmentItem, Shipment
)


async def get_stock_info(session: AsyncSession) -> Dict:
    """
    Получает полную информацию о текущих остатках на складе
    Возвращает:
        {
            "raw_materials": {"Пеллеты 6мм": 500},
            "products": {"Пачки 3кг": 100, "Пачки 5кг": 50}
        }
    """
    # Получаем сырье с названиями
    raw_result = await session.execute(
        select(
            RawProduct.name,
            RawMaterialStorage.amount
        )
        .join(RawMaterialStorage, RawProduct.id == RawMaterialStorage.raw_product_id)
    )
    raw_materials = {name: amount for name, amount in raw_result.all()}

    # Получаем продукцию
    products_result = await session.execute(
        select(Product.name, ProductStorage.amount)
        .join(ProductStorage, Product.id == ProductStorage.product_id)
    )
    products = {name: amount for name, amount in products_result.all()}

    return {
        "raw_materials": raw_materials,
        "products": products
    }


async def get_packaging_stats(
        session: AsyncSession,
        period: str = None,
        start_date: date = None,
        end_date: date = None
) -> Dict[str, int]:
    """
    Получает статистику фасовки продукции
    Параметры:
        period: "month" - за текущий месяц, "custom" - за произвольный период
    Возвращает:
        {"packs_3kg": 100, "packs_5kg": 50}
    """
    query = (
        select(
            func.sum(case((Product.weight == 3, Packaging.amount), else_=0)).label("packs_3kg"),
            func.sum(case((Product.weight == 5, Packaging.amount), else_=0)).label("packs_5kg")
        )
        .select_from(Packaging)
        .join(Product, Packaging.product_id == Product.id)
    )

    if period == "month":
        now = datetime.utcnow()
        query = query.where(
            extract("year", Packaging.date) == now.year,
            extract("month", Packaging.date) == now.month
        )
    elif period == "custom" and start_date and end_date:
        query = query.where(
            Packaging.date >= start_date,
            Packaging.date <= end_date
        )

    result = await session.execute(query)
    stats = result.first()._asdict()
    return {k: v or 0 for k, v in stats.items()}


async def get_arrivals_stats(
        session: AsyncSession,
        period: str = None,
        start_date: date = None,
        end_date: date = None
) -> Dict[str, float]:
    """
    Получает статистику приходов сырья по типам
    Возвращает словарь: {"Тип сырья": количество_кг}
    """
    query = select(
        Arrival.type,
        func.sum(Arrival.amount).label("total_amount")
    )

    if period == "month":
        today = datetime.today()
        first_day = datetime(today.year, today.month, 1)
        query = query.where(Arrival.date >= first_day)
    elif period == "custom" and start_date and end_date:
        query = query.where(
            Arrival.date >= start_date,
            Arrival.date <= end_date
        )

    query = query.group_by(Arrival.type)
    result = await session.execute(query)

    return {arrival_type: amount for arrival_type, amount in result.all()}


async def get_user_expenses(session: AsyncSession, user_id: int) -> float:
    """Получает сумму расходов конкретного пользователя"""
    result = await session.execute(
        select(func.sum(Expense.amount))
        .where(
            Expense.user_id == user_id,
            Expense.source == "собственные средства"
        )
    )
    return result.scalar() or 0


async def get_all_expenses(session: AsyncSession) -> List[Dict]:
    """Получает список всех расходов с информацией о пользователях"""
    result = await session.execute(
        select(
            User.full_name,
            Expense.amount,
            Expense.purpose,
            Expense.date
        )
        .join(User, User.id == Expense.user_id)
        .order_by(Expense.date.desc())
    )

    return [
        {
            "user": full_name,
            "amount": amount,
            "purpose": purpose,
            "date": date.strftime("%d.%m.%Y") if date else None
        }
        for full_name, amount, purpose, date in result.all()
    ]


async def get_detailed_expenses(session: AsyncSession) -> List[Dict]:
    """Получает детализированный список всех расходов"""
    result = await session.execute(
        select(
            User.full_name,
            Expense.amount,
            Expense.purpose,
            Expense.source,
            Expense.date,
            Expense.id
        )
        .join(User, User.id == Expense.user_id)
        .order_by(Expense.date.desc())
    )

    return [
        {
            "id": expense_id,
            "user": full_name,
            "amount": amount,
            "purpose": purpose,
            "source": source,
            "date": date.strftime("%d.%m.%Y %H:%M") if date else None
        }
        for full_name, amount, purpose, source, date, expense_id in result.all()
    ]


async def get_shipments_month_stats(session: AsyncSession):
    """Получение статистики отгрузок за текущий месяц"""
    now = datetime.now()
    start_date = datetime(now.year, now.month, 1)
    end_date = datetime(now.year, now.month + 1, 1) if now.month < 12 else datetime(now.year + 1, 1, 1)

    result = await session.execute(
        select(
            Product.name,
            func.sum(ShipmentItem.quantity).label('total')
        )
        .join(ShipmentItem, ShipmentItem.product_id == Product.id)
        .join(Shipment, Shipment.id == ShipmentItem.shipment_id)
        .where(and_(
            Shipment.timestamp >= start_date,
            Shipment.timestamp < end_date
        ))
        .group_by(Product.name)
    )

    return result.all()


async def get_shipments_period_stats(session: AsyncSession, start_date: datetime, end_date: datetime):
    """Получение статистики отгрузок за указанный период"""
    result = await session.execute(
        select(
            Product.name,
            func.sum(ShipmentItem.quantity).label('total')
        )
        .join(ShipmentItem, ShipmentItem.product_id == Product.id)
        .join(Shipment, Shipment.id == ShipmentItem.shipment_id)
        .where(and_(
            Shipment.timestamp >= start_date,
            Shipment.timestamp <= end_date
        ))
        .group_by(Product.name)
    )

    return result.all()