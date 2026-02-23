from aiogram import Router
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.fsm.shipment import ShipmentStates
from bot.keyboards.shipment import shipment_main_keyboard, shipment_product_keyboard, shipment_add_more_keyboard
from bot.services.shipment import save_shipment, get_available_products, create_shipment, add_product_to_shipment, \
    get_shipment_products, get_user_shipments, complete_shipment
from bot.services.wrapers import restrict_anonymous

router = Router()


@router.message(F.text == "🚚 Отгрузка")
@restrict_anonymous
async def show_shipment_menu(message: types.Message, session: AsyncSession):
    """Меню отгрузки с проверкой доступных продуктов"""
    available_products = await get_available_products(session)

    if not available_products:
        await message.answer("На складе нет доступных продуктов для отгрузки.")
        return

    await message.answer("Управление отгрузками:", reply_markup=shipment_main_keyboard())


@router.callback_query(F.data == "add_shipment")
@restrict_anonymous
async def start_adding_shipment(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    # Создаем новую отгрузку в БД сразу при старте
    shipment = await create_shipment(session, callback.from_user.id)

    # Сохраняем ID созданной отгрузки в состояние
    await state.update_data(shipment_id=shipment.id)
    await state.set_state(ShipmentStates.waiting_for_product)

    # Показываем список товаров

    await callback.message.answer(
        "Выберите товар для добавления в отгрузку:",
        reply_markup= await  shipment_product_keyboard(session)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("product_"), ShipmentStates.waiting_for_product)
@restrict_anonymous
async def process_product_selection(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    product_id = int(callback.data.split("_")[1])
    await state.update_data(selected_product_id=product_id)
    await state.set_state(ShipmentStates.waiting_for_quantity)
    await callback.message.answer("Введите количество:")
    await callback.answer()


@router.message(ShipmentStates.waiting_for_quantity)
@restrict_anonymous
async def process_quantity(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            await message.answer("Пожалуйста, введите положительное число")
            return
    except ValueError:
        await message.answer("Пожалуйста, введите число")
        return

    data = await state.get_data()
    shipment_id = data["shipment_id"]
    product_id = data["selected_product_id"]

    # Добавляем товар в существующую отгрузку
    await add_product_to_shipment(session, shipment_id, product_id, quantity)

    # Проверяем, есть ли уже товары в отгрузке (кроме только что добавленного)
    products = await get_shipment_products(session, shipment_id)

    if len(products) >= 1:  # Если есть хотя бы один товар (текущий)
        await state.set_state(ShipmentStates.waiting_for_more_products)
        await message.answer(
            "Товар добавлен. Хотите добавить еще товар в эту отгрузку?",
            reply_markup=shipment_add_more_keyboard()
        )
    else:
        # Если это первый товар, спрашиваем про добавление следующего
        await state.set_state(ShipmentStates.waiting_for_more_products)
        await message.answer(
            "Товар добавлен. Добавить еще товар в эту отгрузку?",
            reply_markup=shipment_add_more_keyboard()
        )


@router.callback_query(F.data == "add_more", ShipmentStates.waiting_for_more_products)
@restrict_anonymous
async def add_more_products(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    # Возвращаемся к выбору товара для той же отгрузки
    await state.set_state(ShipmentStates.waiting_for_product)
    await callback.message.answer(
        "Выберите следующий товар:",
        reply_markup=await shipment_product_keyboard(session)
    )
    await callback.answer()


@router.callback_query(F.data == "finish_shipment", ShipmentStates.waiting_for_more_products)
@restrict_anonymous
async def finish_shipment(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    shipment_id = data["shipment_id"]

    # Получаем все товары в отгрузке для отображения итога
    products = await get_shipment_products(session, shipment_id)

    # Формируем итоговое сообщение
    total_text = "✅ Отгрузка завершена!\n\nСостав отгрузки:\n"
    for item in products:
        total_text += f"• {item.product.name}: {item.quantity} шт.\n"

    # Завершаем отгрузку (если нужно отметить её как завершенную)
    await complete_shipment(session, shipment_id)

    await state.clear()
    await callback.message.answer(total_text)
    await callback.answer()


@router.callback_query(F.data == "view_shipments")
@restrict_anonymous
async def show_shipments(callback: types.CallbackQuery, session: AsyncSession):

    shipments = await get_user_shipments(session, callback.from_user.id)

    if not shipments:
        await callback.message.answer("У вас пока нет отгрузок.")
        await callback.answer()
        return

    for shipment in shipments:
        products = await get_shipment_products(session, shipment.id)
        text = f"📦 Отгрузка от {shipment.timestamp.strftime('%d.%m.%Y %H:%M')}\n"
        for item in products:
            text += f"  • {item.product.name}: {item.quantity} шт.\n"

        await callback.message.answer(text)

    # await callback.answer()


# @router.callback_query(F.data == "add_shipment")
# @restrict_anonymous
# async def start_shipment_process(
#         callback: types.CallbackQuery,
#         state: FSMContext,
#         session: AsyncSession
# ):
#     """Начало процесса отгрузки"""
#     await callback.answer()
#
#     products = await get_available_products(session)
#
#     # Создаем кнопки для каждого продукта
#     buttons = []
#     for product, amount in products:
#         buttons.append(
#             [InlineKeyboardButton(
#                 text=f"{product.name}\n"
#                      f" (остаток: {amount})",
#                 callback_data=f"select_product:{product.id}"
#             )]
#         )
#
#     keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
#
#     await callback.message.answer(
#         "Выберите продукт для отгрузки:",
#         reply_markup=keyboard
#     )
#     await state.set_state(ShipmentState.selecting_product)
#
#
# @router.callback_query(F.data.startswith("select_product:"), ShipmentState.selecting_product)
# @restrict_anonymous
# async def select_product_for_shipment(
#         callback: types.CallbackQuery,
#         state: FSMContext,
#         session: AsyncSession
# ):
#     """Обработка выбора продукта"""
#     product_id = int(callback.data.split(":")[1])
#     await state.update_data(product_id=product_id)
#     await callback.message.answer("Введите количество для отгрузки:")
#     await state.set_state(ShipmentState.entering_quantity)
#     await callback.answer()
#
#
# @router.message(ShipmentState.entering_quantity)
# @restrict_anonymous
# async def enter_shipment_quantity(
#         message: types.Message,
#         state: FSMContext,
#         session: AsyncSession
# ):
#     """Обработка ввода количества"""
#     try:
#         quantity = int(message.text)
#         if quantity <= 0:
#             raise ValueError
#     except ValueError:
#         await message.answer("Пожалуйста, введите целое положительное число.")
#         return
#
#     data = await state.get_data()
#     product_id = data['product_id']
#
#     try:
#         await save_shipment(
#             telegram_id=message.from_user.id,  # Передаем telegram_id вместо user_id
#             product_id=product_id,
#             quantity=quantity,
#             session=session
#         )
#
#         keyboard = InlineKeyboardMarkup(
#             inline_keyboard=[
#                 [
#                     InlineKeyboardButton(text="✅ Да", callback_data="add_more"),
#                     InlineKeyboardButton(text="❌ Нет", callback_data="finish_shipment")
#                 ]
#             ]
#         )
#
#         await message.answer(
#             "Отгрузка успешно добавлена. Добавить еще продукты?",
#             reply_markup=keyboard
#         )
#         await state.set_state(ShipmentState.adding_more)
#
#     except ValueError as e:
#         await message.answer(str(e))
#         await state.clear()
#
#
# @router.callback_query(F.data == "add_more", ShipmentState.adding_more)
# @restrict_anonymous
# async def add_more_products(
#         callback: types.CallbackQuery,
#         state: FSMContext,
#         session: AsyncSession,
#         **kwargs
# ):
#     # print("Доступные аргументы:", kwargs.keys())
#     """Добавление дополнительных продуктов в отгрузку"""
#     await start_shipment_process(callback, state, session=session)
#
#
# @router.callback_query(F.data == "finish_shipment", ShipmentState.adding_more)
# @restrict_anonymous
# async def finish_shipment_process(
#         callback: types.CallbackQuery,
#         state: FSMContext,
#         session: AsyncSession
# ):
#     """Завершение процесса отгрузки"""
#     await callback.message.answer("Отгрузка завершена.")
#     await state.clear()
#     await callback.answer()


@router.callback_query(F.data == "close_menu")
async def close_menu(callback: types.CallbackQuery):
    """Закрытие меню"""
    await callback.message.delete()

