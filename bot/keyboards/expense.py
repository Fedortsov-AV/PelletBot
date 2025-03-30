from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def expense_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить расход", callback_data="add_expense")],
            [InlineKeyboardButton(text="📜 Список своих расходов", callback_data="view_expenses")],
            [InlineKeyboardButton(text="❌ Закрыть меню", callback_data="close_expense_menu")]
        ]
    )

def expense_source_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Собственные средства", callback_data="expense_source_own")],
            [InlineKeyboardButton(text="🏦 Касса", callback_data="expense_source_cash")]
        ]
    )

def expense_actions_keyboard(expense_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏ Изменить", callback_data=f"edit_expense_{expense_id}")],
            [InlineKeyboardButton(text="🔄 Из кассы", callback_data=f"change_source_{expense_id}")],
            [InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_expense_{expense_id}")]
        ]
    )
