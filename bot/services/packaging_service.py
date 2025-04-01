from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from bot.models import Product, ProductStorage, RawProduct, RawMaterialStorage
from bot.models.packaging import Packaging
from bot.models.arrival import Arrival


async def get_raw_materials(session: AsyncSession):
    """Получаем список сырья с остатками на складе"""
    result = await session.execute(
        select(RawProduct, RawMaterialStorage.amount)
        .join(RawMaterialStorage, RawProduct.id == RawMaterialStorage.raw_product_id)
    )
    return result.all()


async def get_products_for_raw_material(session: AsyncSession, raw_product_id: int):
    """Получаем продукты, которые производятся из указанного сырья"""
    result = await session.execute(
        select(Product, ProductStorage.amount)
        .join(ProductStorage, Product.id == ProductStorage.product_id)
        .where(Product.raw_product_id == raw_product_id)
    )
    return result.all()


async def calculate_packaging_ratio(
        session: AsyncSession,
        raw_product_id: int,
        ratio: str,
        raw_amount: int
):
    """Рассчитываем количество пачек по заданной пропорции"""
    try:
        ratio_parts = list(map(int, ratio.split('/')))
        if len(ratio_parts) != 2:
            return None, "Неверный формат пропорции. Используйте X/Y"

        products = await get_products_for_raw_material(session, raw_product_id)
        if len(products) != 2:
            return None, "Для данного сырья должно быть ровно 2 вида продукции"

        product1, amount1 = products[0]
        product2, amount2 = products[1]

        # Рассчитываем возможное количество пачек
        total_ratio = ratio_parts[0] * product1.weight + ratio_parts[1] * product2.weight
        batches = raw_amount // total_ratio

        packs1 = batches * ratio_parts[0]
        packs2 = batches * ratio_parts[1]

        return {
            product1.name: packs1,
            product2.name: packs2,
            "used_raw": batches * total_ratio
        }, None
    except Exception as e:
        return None, f"Ошибка расчета: {str(e)}"


async def save_packaging(
    session: AsyncSession,
    user_id: int,
    product_id: int,
    raw_product_id: int,
    amount: int,
    used_raw: int
):
    """Сохраняет информацию об одной фасовке"""
    packaging = Packaging(
        product_id=product_id,
        raw_product_id=raw_product_id,
        amount=amount,
        used_raw_material=used_raw,
        user_id=user_id
    )
    session.add(packaging)
    await session.commit()
    return packaging


async def update_stock_after_packaging(
        session: AsyncSession,
        product_id: int,
        raw_product_id: int,
        amount: int,
        used_raw: int
):
    """Обновляет складские остатки после фасовки"""
    from bot.models import ProductStorage, RawMaterialStorage

    # Уменьшаем сырье
    raw_stock = await session.get(RawMaterialStorage, raw_product_id)
    raw_stock.amount -= used_raw

    # Увеличиваем готовую продукцию
    product_stock = await session.execute(
        select(ProductStorage)
        .where(ProductStorage.product_id == product_id)
    )
    product_stock = product_stock.scalar_one()
    product_stock.amount += amount

    await session.commit()


async def check_raw_material_available(
    session: AsyncSession,
    raw_product_id: int,
    required_amount: int
) -> bool:
    """Проверяет, достаточно ли сырья на складе"""
    result = await session.execute(
        select(RawMaterialStorage.amount)
        .where(RawMaterialStorage.raw_product_id == raw_product_id)
    )
    current_amount = result.scalar_one_or_none()
    return current_amount is not None and current_amount >= required_amount


async def update_stock_after_packaging(
        session: AsyncSession,
        product_id: int,
        raw_product_id: int,
        amount: int,
        used_raw: int
):
    """Обновляет складские остатки после фасовки с проверкой"""
    # Уменьшаем сырье
    raw_stock = await session.execute(
        select(RawMaterialStorage)
        .where(RawMaterialStorage.raw_product_id == raw_product_id)
    )
    raw_stock = raw_stock.scalar_one()

    if raw_stock.amount < used_raw:
        raise ValueError("Недостаточно сырья на складе для обновления")

    raw_stock.amount -= used_raw

    # Увеличиваем готовую продукцию
    product_stock = await session.execute(
        select(ProductStorage)
        .where(ProductStorage.product_id == product_id)
    )
    product_stock = product_stock.scalar_one()
    product_stock.amount += amount

    await session.commit()


async def get_raw_material_availability(
        session: AsyncSession,
        raw_product_id: int,
        product_weight: int = None,
        required_amount: int = None
) -> tuple[int, bool, int]:
    """
    Возвращает информацию о доступности сырья:
    - current_amount: текущий остаток сырья (кг)
    - is_available: достаточно ли сырья (если передан required_amount)
    - max_packs: максимальное количество пачек (если передан product_weight)
    """
    result = await session.execute(
        select(RawMaterialStorage.amount)
        .where(RawMaterialStorage.raw_product_id == raw_product_id)
    )
    current_amount = result.scalar_one_or_none() or 0

    max_packs = 0
    if product_weight and product_weight > 0:
        max_packs = current_amount // product_weight

    is_available = True
    if required_amount is not None:
        is_available = current_amount >= required_amount

    return current_amount, is_available, max_packs