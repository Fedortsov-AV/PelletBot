from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.fsm.arrival import ArrivalState
from bot.keyboards.arrival import (
    arrival_types_keyboard, confirm_arrival_keyboard, arrival_main_keyboard
)
from bot.models.database import async_session


from bot.services.arrival import (
    get_arrivals_for_month, add_arrival, update_arrival_amount, get_arrival_by_id, delete_arrival
)
from bot.services.storage import update_stock_arrival, get_raw_material_storage, \
    get_raw_type_at_raw_product_id
from bot.services.user_service import get_user
from bot.services.wrapers import restrict_anonymous, staff_required, track_changes

router = Router()


@router.message(F.text == "Приходы")
@restrict_anonymous
async def show_arrival_menu(message: Message, session: AsyncSession):
    """Показать меню приходов."""
    async with async_session() as session:
        user = await get_user(session, message.from_user.id)
        if not user:
            await message.answer("❌ У вас нет доступа к функции 'Приходы'.")
            return
    await message.answer("Выберите действие:", reply_markup=arrival_main_keyboard(user.role))


@router.callback_query(F.data == "add_arrival")
@restrict_anonymous
async def add_arrival_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Начать процесс добавления прихода."""
    keyboard = await arrival_types_keyboard(session)
    await callback.message.answer("Выберите тип продукции:", reply_markup=keyboard)
    await state.set_state(ArrivalState.type)


@router.callback_query(F.data.startswith("arrival_type:"))
async def set_arrival_type(callback: CallbackQuery, state: FSMContext):
    """Установка типа продукции."""
    raw_product_id = int(callback.data.split(":")[1])
    await state.update_data(raw_product_id=raw_product_id)
    await callback.message.edit_text(f"Введите количество (кг):")
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
    📦 Количество: {data['amount']} кг    
    """
    await message.answer(text, reply_markup=confirm_arrival_keyboard())
    await state.set_state(ArrivalState.confirm)


@router.callback_query(F.data == "arrival_confirm")
@track_changes("поступления")
async def confirm_arrival(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждение добавления прихода."""
    data = await state.get_data()

    arrival = await add_arrival(session, callback.from_user.id, data["raw_product_id"], data["amount"])
    print(f"Создан приход ID: {arrival.id}")
    await callback.message.edit_text("✅ Приход успешно добавлен!")
    await state.clear()
    return arrival

@router.callback_query(F.data == "arrival_cancel")
async def cancel_arrival(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления прихода."""
    await callback.message.edit_text("❌ Добавление прихода отменено.")
    await state.clear()


@router.callback_query(F.data == "view_arrivals")
@staff_required
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
@staff_required
@track_changes("поступления")
async def delete_arrival_handler(callback: CallbackQuery, session: AsyncSession):
    print("=== HANDLER DELETE CALLED ===")
    arrival_id = int(callback.data.split(":")[1])
    await delete_arrival(session, arrival_id)
    await callback.message.answer(f"✅ Приход {arrival_id} успешно удалён!")
    await callback.answer()

# @router.callback_query(F.data.startswith("delete_arrival:"))
# @staff_required
# @track_changes("поступления")
# async def delete_arrival_handler(callback: CallbackQuery, session: AsyncSession):
#     """Удаление прихода и обновление склада."""
#     arrival_id = int(callback.data.split(":")[1])
#     arival = await get_arrival_by_id(session, arrival_id)
#     raw_storage = await  get_raw_material_storage(session, arrival_id)
#     raw_type = await get_raw_type_at_raw_product_id(session, raw_storage.raw_product_id)
#     delta = 0 - arival.amount
#     await  update_stock_arrival(session, raw_type, delta)
#     await session.delete(arival)
#     await session.commit()
#
#     await callback.message.answer(f"✅ Приход {arrival_id} успешно удалён!")
#     await callback.answer()
#     return arival


@router.callback_query(F.data.startswith("edit_arrival:"))
@staff_required
async def edit_arrival_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Редактирование количества прихода."""
    arrival_id = int(callback.data.split(":")[1])
    await state.update_data(arrival_id=arrival_id)
    await callback.message.answer("Введите новое количество (кг):")
    await state.set_state(ArrivalState.amount_edit)


@router.message(ArrivalState.amount_edit, F.text.isdigit())
@track_changes("поступления")
async def set_arrival_amount_edit_handler(message: Message, state: FSMContext, session: AsyncSession):
    new_amount = int(message.text)
    if new_amount <= 0:
        await message.answer("Ошибка: количество должно быть больше 0.")
        return
    data = await state.get_data()
    arrival_id = data['arrival_id']
    arrival = await update_arrival_amount(session, arrival_id, new_amount)
    if arrival:
        await message.answer(f"✅ Количество прихода ID={arrival_id} изменено на {new_amount} кг.")
    else:
        await message.answer("Приход не найден.")
    await state.clear()

# @router.message(ArrivalState.amount_edit, F.text.isdigit())
# @track_changes("поступления")
# async def set_arrival_amount_edit_handler(message: Message, state: FSMContext, session: AsyncSession):
#     """Редактирование типа родукции прихода"""
#     new_amount = int(message.text)
#     if new_amount <= 0:
#         await message.answer("Ошибка: количество должно быть больше 0.")
#         return
#
#     await state.update_data(arrival_amount=new_amount)
#
#     keyboard = await arrival_types_keyboard_for_edit(session)
#     await message.answer("Выберите тип продукции:", reply_markup=keyboard)
#     await state.set_state(ArrivalState.type_edit)


# @router.callback_query(ArrivalState.type_edit, F.data.startswith("arrival_type_edit:"))
# @track_changes("поступления")
# async def update_arrival_type_edit_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
#     """Обновление количества прихода и склада."""
#     arrival_type = callback.data.split(":")[1]
#
#     data = await state.get_data()
#     arrival_id = data['arrival_id']
#     arrival_amount = data['arrival_amount']
#
#     arrival = await update_arrival_amount(session, arrival_id, arrival_amount, arrival_type)
#
#     await callback.message.answer(
#         f"✅ Количество прихода {arrival_type} ID={arrival_id} изменено на {arrival_amount} кг.")
#     await state.clear()
#     return arrival