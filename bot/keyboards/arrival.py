from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.arrival import get_raw_product_names


def arrival_types_keyboard(session: AsyncSession):
    builder = InlineKeyboardBuilder()
    products = get_raw_product_names(session)

    for product in products:
        builder.button(text=product, callback_data=f"arrival_type:{product}")

    builder.adjust(2)
    return builder.as_markup()


def confirm_arrival_keyboard():
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="arrival_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="arrival_cancel")
    ).as_markup()

def arrival_main_keyboard(role: str) -> InlineKeyboardMarkup:
    """Главное меню для обработки приходов с учётом роли пользователя."""
    buttons = [

    ]

    if role in ["admin", "manager", "operator"]:
        buttons.append([InlineKeyboardButton(text="✅ Добавить приход", callback_data="add_arrival")])


    # Только для менеджеров и администраторов добавляем кнопку "Приходы за месяц"
    if role in ["admin", "manager"]:
        buttons.append([InlineKeyboardButton(text="📅 Приходы за месяц", callback_data="view_arrivals")])

    buttons.append([InlineKeyboardButton(text="❌ Закрыть меню", callback_data="close_menu")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)