from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.fsm.expense import ExpenseStates
from bot.keyboards.expense import expense_main_keyboard, expense_source_keyboard, expense_actions_keyboard
from bot.services.expense import add_expense, get_expenses, update_expense, change_expense_source, delete_expense
from bot.services.user_service import get_user
from bot.services.wrapers import staff_required

router = Router()


@router.message(F.text == "💸 Расходы")
@staff_required
async def show_expense_menu(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=expense_main_keyboard())


@router.callback_query(F.data == "add_expense")
@staff_required
async def start_adding_expense(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ExpenseStates.waiting_for_amount)
    await callback.message.answer("Введите сумму расхода:")
    await callback.answer()


@router.message(ExpenseStates.waiting_for_amount)
@staff_required
async def process_expense_amount(message: types.Message, state: FSMContext):
    await state.update_data(amount=int(message.text))
    await state.set_state(ExpenseStates.waiting_for_purpose)
    await message.answer("Введите назначение расхода:")


@router.message(ExpenseStates.waiting_for_purpose)
@staff_required
async def process_expense_purpose(message: types.Message, state: FSMContext):
    await state.update_data(purpose=message.text)
    await state.set_state(ExpenseStates.waiting_for_source)
    await message.answer("Выберите источник расходов:", reply_markup=expense_source_keyboard())


@router.callback_query(F.data.startswith("expense_source_"))
@staff_required
async def process_expense_source(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    source = "собственные средства" if callback.data == "expense_source_own" else "касса"
    user = await get_user(session, callback.from_user.id)
    await add_expense(session, user.id, data["amount"], data["purpose"], source)
    await state.clear()
    await callback.message.answer("Расход успешно добавлен.")
    await callback.answer()


@router.callback_query(F.data == "view_expenses")
@staff_required
async def show_expenses(callback: CallbackQuery, session: AsyncSession):
    user = await get_user(session, callback.from_user.id)
    expenses = await get_expenses(session, user.id)

    if not expenses:
        await callback.message.answer("У вас нет расходов из собственных средств.")
        return

    for expense in expenses:
        text = f"📅 {expense.date.strftime('%d.%m.%Y')}\n💰 {expense.amount} руб.\n📝 {expense.purpose}"
        await callback.message.answer(text, reply_markup=expense_actions_keyboard(expense.id))

    await callback.answer()


@router.callback_query(F.data.startswith("edit_expense_"))
@staff_required
async def start_editing_expense(callback: CallbackQuery, state: FSMContext):
    expense_id = int(callback.data.split("_")[-1])
    await state.update_data(expense_id=expense_id)
    await state.set_state(ExpenseStates.waiting_for_new_amount)
    await callback.message.answer("Введите новую сумму расхода:")


@router.message(ExpenseStates.waiting_for_new_amount)
@staff_required
async def process_new_expense_amount(message: types.Message, state: FSMContext):
    await state.update_data(amount=int(message.text))
    await state.set_state(ExpenseStates.waiting_for_new_purpose)
    await message.answer("Введите новое назначение расхода:")


@router.message(ExpenseStates.waiting_for_new_purpose)
@staff_required
async def process_new_expense_purpose(message: types.Message, state: FSMContext, session: AsyncSession):
    await state.update_data(purpose=message.text)
    data = await state.get_data()
    print("FSM Data before update_expense:", data)
    await update_expense(session, data["expense_id"], data["amount"], data["purpose"])
    await state.clear()
    await message.answer("Расход успешно обновлен.")


@router.callback_query(F.data.startswith("delete_expense_"))
@staff_required
async def delete_expense_handler(callback: CallbackQuery, session: AsyncSession):
    expense_id = int(callback.data.split("_")[-1])
    await delete_expense(session, expense_id)
    await callback.message.answer("Расход удален.")

@router.callback_query(F.data.startswith("change_source_"))
@staff_required
async def change_expense_source_handler(callback: CallbackQuery, session: AsyncSession):
    expense_id = int(callback.data.split("_")[-1])
    await change_expense_source(session, expense_id)
    await callback.message.answer("Источник расхода изменен на 'касса'.")
    await callback.answer()

@router.callback_query(F.data == "close_expense_menu")
@staff_required
async def close_expense_menu(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()
