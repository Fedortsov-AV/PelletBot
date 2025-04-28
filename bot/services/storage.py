from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from bot.models import RawMaterialStorage, RawProduct, Arrival


# 🏭 Получить текущий склад (если нет — создать)
async def get_raw_material_storage(session: AsyncSession, arrival_id: int):
    # Получаем тип материала из таблицы Arrival
    result = await session.execute(select(Arrival.type).filter(Arrival.id == arrival_id))
    arrival_type = result.scalar_one_or_none()



    if not arrival_type:
        raise ValueError(f"Приход с id {arrival_id} не найден.")

    # Ищем запись в RawMaterialStorage по этому типу
    result = await session.execute(
        select(RawMaterialStorage).join(RawProduct).filter(RawProduct.name == arrival_type)
    )
    stock = result.scalar_one_or_none()

    if not stock:
        raise ValueError(f"Материал '{arrival_type}' не найден на складе.")

    return stock



async def get_raw_type_at_raw_product_id(session: AsyncSession, id: int):
    """
        Получает поле name из таблицы RawProduct по заданному id.
        """
    result = await session.execute(select(RawProduct.name).filter(RawProduct.id == id))
    return result.scalar_one_or_none()


# ➕ Обновить приход пеллет (атомарно)
async def update_stock_arrival(session: AsyncSession, type: str, amount: int):
    """
    Обновить склад после прихода продукции.
    Увеличивает количество материала на складе на основе суммы прихода.
    """
    # Получаем ID продукта по имени type
    result = await session.execute(select(RawProduct.id).filter(RawProduct.name == type))
    product_id = result.scalar_one_or_none()


    if not product_id:
        # Если продукт с таким именем не найден, выбрасываем ошибку
        raise ValueError(f"Продукт с именем {type} не найден в базе данных.")

    # Получаем данные о продукте на складе
    all_stock = await session.execute(select(RawMaterialStorage).options(selectinload(RawMaterialStorage.raw_product)))
    stock = all_stock.scalars().all()  # Получаем все записи склада


    # Проходим по всем материалам на складе и обновляем их
    for item in stock:
        if item.raw_product.id == product_id:  # Сравниваем по ID продукта
            item.amount += amount  # Увеличиваем количество на складе
            session.add(item)  # Сохраняем изменения

    # Если продукта нет в базе (например, нет записи в raw_material_storage), добавляем новую запись
    if not any(item.raw_product.id == product_id for item in stock):
        new_item = RawMaterialStorage(raw_product_id=product_id, amount=amount)  # Используем найденный ID продукта
        session.add(new_item)

    # await session.commit()  # Подтверждаем изменения в БД

# ➖ Обновить после фасовки (атомарно)


async def edit_stock_arival(session: AsyncSession, arrival_id: int, new_amount: int):
    """Обновление количества прихода и склада"""
    arrival = await session.get(Arrival, arrival_id)

    # if not arrival:
    #     await message.answer("❌ Приход не найден.")
    #     return

    delta = arrival.amount - new_amount
    arrival.amount = new_amount
    await update_stock_arrival(session, arrival.type, amount=delta*(-1))



