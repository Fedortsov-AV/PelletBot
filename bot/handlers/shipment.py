from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.fsm.shipment import ShipmentState
from aiogram import Router
from bot.services.shipment import save_shipment, update_stock_after_shipment  # Сервисы для работы с БД
from bot.services.storage import get_raw_material_storage

# Создаем экземпляр Router
router = Router()

# Отображаем меню отгрузки с инлайн кнопками
@router.message(F.text == "🚚 Отгрузка")
async def show_shipment_menu(message: types.Message):
    """Показываем меню отгрузки с эмодзи как изображениями в кнопках"""

    # Создание инлайн-клавиатуры с эмодзи в кнопках
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 Добавить отгрузку", callback_data="add_shipment"),
            InlineKeyboardButton(text="❌ Закрыть меню", callback_data="close_shipment_menu")
        ]
    ])

    # Отправляем сообщение с клавиатурой
    await message.answer("Выберите действие:", reply_markup=keyboard)
# Хендлер для кнопки "Добавить отгрузку"
@router.callback_query(F.data == "add_shipment")
async def add_shipment_step1(callback_query: types.CallbackQuery, state: FSMContext):
    """Запрашиваем количество отгруженных пачек по 3 кг"""
    await callback_query.answer()  # Отвечаем на запрос, чтобы убрать крутящийся индикатор
    await callback_query.message.answer("Сколько пачек по 3 кг было отгружено?")
    await state.set_state(ShipmentState.waiting_for_small_packs)


# @router.callback_query(Text("add_shipment"))
# async def add_shipment(call: types.CallbackQuery, state: FSMContext):
#     """Запросить количество пачек по 3 кг"""
#     await call.message.answer("Сколько пачек по 3 кг было отгружено?")
#     await state.set_state(ShipmentState.waiting_for_small_packs)  # Устанавливаем состояние ожидания


@router.message(ShipmentState.waiting_for_small_packs)
async def get_small_packs(message: types.Message, state: FSMContext):
    """Получаем количество пачек 3 кг"""
    try:
        small_packs = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите количество целыми числами.")
        return

    # Сохраняем количество в состоянии
    await state.update_data(small_packs=small_packs)

    # Запрашиваем количество пачек по 5 кг
    await message.answer("Сколько пачек по 5 кг было отгружено?")
    await state.set_state(ShipmentState.waiting_for_large_packs)  # Переходим в следующее состояние


@router.message(ShipmentState.waiting_for_large_packs)
async def get_large_packs(message: types.Message, state: FSMContext, session: AsyncSession):
    """Получаем количество пачек 5 кг"""
    try:
        large_packs = int(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите количество целыми числами.")
        return

    # Получаем данные из состояния
    user_data = await state.get_data()
    small_packs = user_data.get("small_packs")

    await save_shipment(user_id=message.from_user.id, small_packs=small_packs, large_packs=large_packs, session=session)

    # Обновляем остатки на складе
    await update_stock_after_shipment(small_packs=small_packs, large_packs=large_packs, session=session)

    # Завершаем процесс
    await message.answer(f"Отгрузка завершена: {small_packs} пачек по 3 кг и {large_packs} пачек по 5 кг.")

    # Закрываем состояние
    await state.clear()

# Хендлер для кнопки "Закрыть меню"
@router.callback_query(F.data == "close_shipment_menu")
async def close_shipment_menu(callback_query: types.CallbackQuery):
    """Закрытие меню отгрузки"""
    await callback_query.message.delete()
    await callback_query.answer()
