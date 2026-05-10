from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from bot.models.material_movement import MaterialMovement
from bot.models.packaging_material import PackagingMaterial
from bot.models.expense import Expense

async def get_available_inventory(session: AsyncSession, material_id: int):
    """Возвращает список приходных записей с ненулевым остатком, отсортированных по дате."""
    result = await session.execute(
        select(MaterialMovement)
        .where(
            MaterialMovement.material_id == material_id,
            MaterialMovement.type == 'in',
            MaterialMovement.remaining_quantity > 0
        )
        .order_by(MaterialMovement.date)
    )
    return result.scalars().all()

async def consume_material(session: AsyncSession, material_id: int, needed_qty: float, packaging_id: int):
    """Списывает нужное количество материала по FIFO, записывает стоимость в PackagingMaterial.
    Возвращает общую стоимость списанного материала."""
    total_cost = 0.0
    remaining = needed_qty
    inventory = await get_available_inventory(session, material_id)

    for batch in inventory:
        if remaining <= 0:
            break
        take = min(batch.remaining_quantity, remaining)
        cost = round(take * batch.unit_price, 2)
        total_cost += cost

        # Создаём запись расхода материала
        out_movement = MaterialMovement(
            material_id=material_id,
            type='out',
            quantity=take,
            unit=batch.unit,
            date=func.now(),
            packaging_id=packaging_id
        )
        session.add(out_movement)

        # Создаём запись в packaging_materials
        pm = PackagingMaterial(
            packaging_id=packaging_id,
            material_id=material_id,
            quantity=take,
            unit=batch.unit,
            cost=cost
        )
        session.add(pm)

        # Уменьшаем остаток партии
        batch.remaining_quantity -= take
        remaining -= take

    remaining = round(remaining, 2)
    if remaining > 0.005:  # всё, что меньше 0.005, считаем нулём
        raise ValueError(f"Недостаточно материала (id={material_id}) на складе. Не хватает {remaining}")

    return total_cost


async def purchase_material(
    session: AsyncSession,
    material_id: int,
    quantity: float,
    unit: str,
    unit_price: float,
    expense_amount: float = None,
    user_id: int = None
) -> MaterialMovement:
    """Закупка материала: создаёт приходную запись и, опционально, расход в финансах."""
    # Создаём приходное движение
    movement = MaterialMovement(
        material_id=material_id,
        type='in',
        quantity=quantity,
        unit=unit,
        unit_price=unit_price,
        remaining_quantity=quantity,
        date=func.now()
    )
    session.add(movement)
    await session.flush()

    # Если передана сумма и пользователь, создаём запись в expenses
    if expense_amount and user_id:
        expense = Expense(
            amount=expense_amount,
            purpose=f"Закупка материала (ID={material_id})",
            source="собственные средства",  # или можно передавать параметром
            category="packaging_material",
            material_id=material_id,
            quantity=quantity,
            unit=unit,
            user_id=user_id,
            date=func.now()
        )
        session.add(expense)

    await session.commit()
    return movement

async def return_material(
    session: AsyncSession,
    material_id: int,
    quantity: float,
    unit: str,
    unit_price: float,
    packaging_id: int
):
    """Возврат материала на склад (отмена расхода) — создаёт приходную запись."""
    movement = MaterialMovement(
        material_id=material_id,
        type='in',
        quantity=quantity,
        unit=unit,
        unit_price=unit_price,
        remaining_quantity=quantity,   # полностью доступен для будущих списаний
        date=func.now(),
        packaging_id=packaging_id
    )
    session.add(movement)
    return movement