from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.fsm.shipment import ShipmentState
from bot.services.shipment import save_shipment, get_available_products
from aiogram import Router

router = Router()


@router.message(F.text == "🚚 Отгрузка")
async def show_shipment_menu(message: types.Message, session: AsyncSession):
    """Меню отгрузки с проверкой доступных продуктов"""
    available_products = await get_available_products(session)

    if not available_products:
        await message.answer("На складе нет доступных продуктов для отгрузки.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 Добавить отгрузку", callback_data="add_shipment"),
                InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
            ]
        ]
    )
    await message.answer("Выберите действие:", reply_markup=keyboard)

@router.callback_query(F.data == "add_shipment")
async def start_shipment_process(
        callback: types.CallbackQuery,
        state: FSMContext,
        session: AsyncSession
):
    """Начало процесса отгрузки"""
    await callback.answer()

    products = await get_available_products(session)

    # Создаем кнопки для каждого продукта
    buttons = []
    for product, amount in products:
        buttons.append(
            [InlineKeyboardButton(
                text=f"{product.name} (остаток: {amount})",
                callback_data=f"select_product:{product.id}"
            )]
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.answer(
        "Выберите продукт для отгрузки:",
        reply_markup=keyboard
    )
    await state.set_state(ShipmentState.selecting_product)


@router.callback_query(F.data.startswith("select_product:"), ShipmentState.selecting_product)
async def select_product_for_shipment(
    callback: types.CallbackQuery,
    state: FSMContext
):
    """Обработка выбора продукта"""
    product_id = int(callback.data.split(":")[1])
    await state.update_data(product_id=product_id)
    await callback.message.answer("Введите количество для отгрузки:")
    await state.set_state(ShipmentState.entering_quantity)
    await callback.answer()


@router.message(ShipmentState.entering_quantity)
async def enter_shipment_quantity(
        message: types.Message,
        state: FSMContext,
        session: AsyncSession
):
    """Обработка ввода количества"""
    try:
        quantity = int(message.text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите целое положительное число.")
        return

    data = await state.get_data()
    product_id = data['product_id']

    try:
        await save_shipment(
            telegram_id=message.from_user.id,  # Передаем telegram_id вместо user_id
            product_id=product_id,
            quantity=quantity,
            session=session
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data="add_more"),
                    InlineKeyboardButton(text="❌ Нет", callback_data="finish_shipment")
                ]
            ]
        )

        await message.answer(
            "Отгрузка успешно добавлена. Добавить еще продукты?",
            reply_markup=keyboard
        )
        await state.set_state(ShipmentState.adding_more)

    except ValueError as e:
        await message.answer(str(e))
        await state.clear()


@router.callback_query(F.data == "add_more", ShipmentState.adding_more)
async def add_more_products(
    callback: types.CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """Добавление дополнительных продуктов в отгрузку"""
    await start_shipment_process(callback, state, session)


@router.callback_query(F.data == "finish_shipment", ShipmentState.adding_more)
async def finish_shipment_process(
    callback: types.CallbackQuery,
    state: FSMContext
):
    """Завершение процесса отгрузки"""
    await callback.message.answer("Отгрузка завершена.")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "close_menu")
async def close_menu(callback: types.CallbackQuery):
    """Закрытие меню"""
    await callback.message.delete()
    await callback.answer()