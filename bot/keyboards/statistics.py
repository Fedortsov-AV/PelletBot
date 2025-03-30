from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.testing import rowset


def statistics_keyboard() -> InlineKeyboardMarkup:
    buttons = []


    # Первая строка (3 кнопки)
    buttons.append([InlineKeyboardButton(text="📦 Остатки на складе", callback_data="statistics:stock")])
    buttons.append([InlineKeyboardButton(text="📊 Расфасовано за месяц", callback_data="statistics:packed_month")])
    buttons.append([InlineKeyboardButton(text="📆 Расфасовано за", callback_data="statistics:packed_period")])

    # Вторая строка (3 кнопки)
    buttons.append([InlineKeyboardButton(text="📥 Сумма приходов за месяц", callback_data="statistics:arrivals_month")])
    buttons.append([InlineKeyboardButton(text="📆 Сумма приходов за", callback_data="statistics:arrivals_period")])
    buttons.append([InlineKeyboardButton(text="💰 Расходы СС", callback_data="statistics:expenses_user")])

    # Третья строка (2 кнопки)
    buttons.append([InlineKeyboardButton(text="📜 Список всех расходов", callback_data="statistics:expenses_all")])
    buttons.append([InlineKeyboardButton(text="❌ Закрыть меню", callback_data="statistics:close")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
