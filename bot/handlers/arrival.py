from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from select import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from sqlalchemy.orm import session

from bot.keyboards.arrival import arrival_types_keyboard, confirm_arrival_keyboard, arrival_main_keyboard
from bot.models.arrival import Arrival
from bot.fsm.arrival import ArrivalState
from bot.models.database import async_session
from bot.services.arrival import process_arrival, get_arrivals_for_month, delete_arrival, update_arrival_amount
from bot.services.user_service import get_user

router = Router()

@router.message(F.text == "Приходы")
async def show_arrival_menu(message: Message):
    """Показать меню с выбором для работы с приходами"""
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)

        if not user:
            await message.answer("❌ У вас нет доступа к функции 'Приходы'.")
            return
    await message.answer("Выберите действие:", reply_markup=arrival_main_keyboard(user.role))

# Обработчик для добавления прихода
@router.callback_query(F.data == "add_arrival")
async def add_arrival_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    """Начать процесс добавления прихода"""
    await callback.message.answer("Выберите тип продукции:", reply_markup=arrival_types_keyboard())
    await state.set_state(ArrivalState.type)

@router.callback_query(F.data.startswith("arrival_type:"))
async def set_arrival_type(callback: CallbackQuery, state: FSMContext):
    product_type = callback.data.split(":")[1]
    await state.update_data(type=product_type)
    await callback.message.edit_text(f"Вы выбрали: {product_type}\nВведите количество (кг):")
    await state.set_state(ArrivalState.amount)

@router.message(ArrivalState.amount, F.text.isdigit())
async def set_arrival_amount(message: Message, state: FSMContext):
    amount = int(message.text)
    if amount <= 0:
        await message.answer("Ошибка: количество должно быть больше 0.")
        return

    await state.update_data(amount=amount)
    data = await state.get_data()
    text = f"""
    📌 Новый приход:
    🏷️ Тип: {data['type']}
    📦 Количество: {data['amount']} кг    
    """
    await message.answer(text, reply_markup=confirm_arrival_keyboard())
    await state.set_state(ArrivalState.confirm)


@router.callback_query(F.data == "arrival_confirm")
async def confirm_arrival(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    arrival = Arrival(
        type=data["type"],
        amount=data["amount"],
        user_id=callback.from_user.id,
        date=datetime.utcnow(),
    )
    session.add(arrival)
    await session.commit()

    await callback.message.edit_text("✅ Приход успешно добавлен!")
    await state.clear()

@router.callback_query(F.data == "arrival_cancel")
async def cancel_arrival(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Добавление прихода отменено.")
    await state.clear()

# Обработчик для редактирования количества прихода
@router.callback_query(F.data.startswith("edit_arrival:"))
async def edit_arrival_handler(callback: CallbackQuery, state: FSMContext):
    """Запрос нового количества для редактирования прихода"""
    arrival_id = int(callback.data.split(":")[1])
    await state.update_data(arrival_id=arrival_id)
    await callback.message.answer("Введите новое количество (кг):")
    await state.set_state(ArrivalState.amount_edit)

# Обработчик для отображения приходов за месяц
@router.callback_query(F.data == "view_arrivals")
async def view_arrivals_handler(callback: CallbackQuery, session: AsyncSession):
    """Показать приход за месяц с возможностью редактирования и удаления"""
    arrivals = await get_arrivals_for_month(session, callback.from_user.id)

    if not arrivals:
        await callback.message.answer("Приходы за этот месяц отсутствуют.")
        await callback.answer()
        return

    # Отправляем список приходов
    for arrival in arrivals:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_arrival:{arrival.id}")],
                [InlineKeyboardButton(text="✏️ Изменить", callback_data=f"edit_arrival:{arrival.id}")]
            ]
        )
        await callback.message.answer(
            f"📅 Приход от {arrival.date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📦 Количество: {arrival.amount} кг",
            reply_markup=keyboard
        )
    await callback.answer()

# Обработчик для удаления прихода
@router.callback_query(F.data.startswith("delete_arrival:"))
async def delete_arrival_handler(callback: CallbackQuery, session: AsyncSession):
    """Удаление записи о приходе"""
    arrival_id = int(callback.data.split(":")[1])
    arrival = await delete_arrival(session, arrival_id)

    if arrival:
        await callback.message.answer(f"✅ Приход {arrival.id} успешно удалён!")
    else:
        await callback.message.answer("❌ Приход не найден.")
    await callback.answer()

# Обработчик для изменения количества прихода
@router.message(ArrivalState.amount_edit, F.text.isdigit())
async def set_arrival_amount_edit_handler(message: Message, state: FSMContext, session: AsyncSession):
    """Обновление количества продукции в приходе"""
    new_amount = int(message.text)
    if new_amount <= 0:
        await message.answer("Ошибка: количество должно быть больше 0.")
        return

    data = await state.get_data()
    arrival_id = data['arrival_id']

    # Обновляем количество
    arrival = await update_arrival_amount(session, arrival_id, new_amount)

    if arrival:
        await message.answer(f"✅ Количество прихода {arrival.id} изменено на {new_amount} кг.")
    else:
        await message.answer("❌ Приход не найден.")
    await state.clear()

# Обработчик для закрытия меню
@router.callback_query(F.data == "close_menu")
async def close_menu_handler(callback: CallbackQuery):
    """Закрытие меню"""
    await callback.message.delete()
    await callback.answer()