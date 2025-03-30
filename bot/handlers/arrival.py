from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from bot.keyboards.arrival import (
    arrival_types_keyboard, confirm_arrival_keyboard, arrival_main_keyboard
)
from bot.models.arrival import Arrival
from bot.models.database import async_session
from bot.fsm.arrival import ArrivalState
from bot.services.arrival import (
    get_arrivals_for_month, delete_arrival
)
from bot.services.storage import get_stock, update_stock_arrival, update_stock_packaging
from bot.services.user_service import get_user

router = Router()


@router.message(F.text == "Приходы")
async def show_arrival_menu(message: Message):
    """Показать меню приходов."""
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)
        if not user:
            await message.answer("❌ У вас нет доступа к функции 'Приходы'.")
            return
    await message.answer("Выберите действие:", reply_markup=arrival_main_keyboard(user.role))


@router.callback_query(F.data == "add_arrival")
async def add_arrival_handler(callback: CallbackQuery, state: FSMContext):
    """Начать процесс добавления прихода."""
    await callback.message.answer("Выберите тип продукции:", reply_markup=arrival_types_keyboard())
    await state.set_state(ArrivalState.type)


@router.callback_query(F.data.startswith("arrival_type:"))
async def set_arrival_type(callback: CallbackQuery, state: FSMContext):
    """Установка типа продукции."""
    product_type = callback.data.split(":")[1]
    await state.update_data(type=product_type)
    await callback.message.edit_text(f"Вы выбрали: {product_type}\nВведите количество (кг):")
    await state.set_state(ArrivalState.amount)


@router.message(ArrivalState.amount, F.text.isdigit())
async def set_arrival_amount(message: Message, state: FSMContext):
    """Запись количества продукции."""
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
    """Подтверждение добавления прихода."""
    data = await state.get_data()

    async with session.begin():  # Атомарная операция
        arrival = Arrival(
            type=data["type"],
            amount=data["amount"],
            user_id=callback.from_user.id,
            date=datetime.utcnow(),
        )
        session.add(arrival)

        # Вызов обновления склада с передачей всех аргументов
        await update_stock_arrival(session,  data["amount"])

    await callback.message.edit_text("✅ Приход успешно добавлен!")
    await state.clear()


@router.callback_query(F.data == "arrival_cancel")
async def cancel_arrival(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления прихода."""
    await callback.message.edit_text("❌ Добавление прихода отменено.")
    await state.clear()


@router.callback_query(F.data == "view_arrivals")
async def view_arrivals_handler(callback: CallbackQuery, session: AsyncSession):
    """Отображение приходов за месяц."""
    arrivals = await get_arrivals_for_month(session, callback.from_user.id)

    if not arrivals:
        await callback.message.answer("Приходы за этот месяц отсутствуют.")
        await callback.answer()
        return

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


@router.callback_query(F.data.startswith("delete_arrival:"))
async def delete_arrival_handler(callback: CallbackQuery, session: AsyncSession):
    """Удаление прихода и обновление склада."""
    arrival_id = int(callback.data.split(":")[1])

    async with session.begin():
        arrival = await session.get(Arrival, arrival_id)
        if not arrival:
            await callback.message.answer("❌ Приход не найден.")
            return

        # Уменьшаем количество на складе
        await update_stock_packaging(session, arrival.amount, 0, 0)  # Просто уменьшаем пеллеты

        await session.delete(arrival)

    await callback.message.answer(f"✅ Приход {arrival_id} успешно удалён!")
    await callback.answer()


@router.callback_query(F.data.startswith("edit_arrival:"))
async def edit_arrival_handler(callback: CallbackQuery, state: FSMContext):
    """Редактирование количества прихода."""
    arrival_id = int(callback.data.split(":")[1])
    await state.update_data(arrival_id=arrival_id)
    await callback.message.answer("Введите новое количество (кг):")
    await state.set_state(ArrivalState.amount_edit)


@router.message(ArrivalState.amount_edit, F.text.isdigit())
async def set_arrival_amount_edit_handler(message: Message, state: FSMContext, session: AsyncSession):
    """Обновление количества прихода и склада."""
    new_amount = int(message.text)
    if new_amount <= 0:
        await message.answer("Ошибка: количество должно быть больше 0.")
        return

    data = await state.get_data()
    arrival_id = data['arrival_id']

    async with session.begin():
        arrival = await session.get(Arrival, arrival_id)
        if not arrival:
            await message.answer("❌ Приход не найден.")
            return

        # Корректируем склад
        delta = new_amount - arrival.amount
        await update_stock_arrival(session, delta)  # Изменяем склад

        arrival.amount = new_amount

    await message.answer(f"✅ Количество прихода {arrival_id} изменено на {new_amount} кг.")
    await state.clear()
