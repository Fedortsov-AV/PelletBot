from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constants.roles import ADMIN, MANAGER, OPERATOR
from bot.services.arrival import get_raw_product_names, get_raw_products


async def arrival_types_keyboard(session: AsyncSession):
    raw_products = await get_raw_products(session)
    if not raw_products:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Нет продукции", callback_data="no_product")]
        ])
    buttons = [
        [InlineKeyboardButton(text=rp.name, callback_data=f"arrival_type:{rp.id}")]
        for rp in raw_products
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# async def arrival_types_keyboard(session: AsyncSession):
#     buttons = []
#     products = await  get_raw_product_names(session)
#     if not products:
#         return InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="Нет продукции", callback_data="no_product")]
#         ])
#     for product in products:
#         buttons.append([InlineKeyboardButton(text=product, callback_data=f"arrival_type:{product}")])
#
#     return InlineKeyboardMarkup(inline_keyboard=buttons)


# async def arrival_types_keyboard_for_edit(session: AsyncSession):
#     buttons = []
#     products = await  get_raw_product_names(session)
#     if not products:
#         return InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="Нет продукции", callback_data="no_product")]
#         ])
#     for product in products:
#         buttons.append([InlineKeyboardButton(text=product, callback_data=f"arrival_type_edit:{product}")])
#
#     return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_arrival_keyboard():
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="arrival_confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="arrival_cancel")
    ).as_markup()


def arrival_main_keyboard(role: str) -> InlineKeyboardMarkup:
    buttons = []
    if role in [ADMIN, MANAGER, OPERATOR]:
        buttons.append([InlineKeyboardButton(text="✅ Добавить приход", callback_data="add_arrival")])
    if role in [ADMIN, MANAGER]:
        buttons.append([InlineKeyboardButton(text="📅 Приходы за месяц", callback_data="view_arrivals")])
    buttons.append([InlineKeyboardButton(text="❌ Закрыть меню", callback_data="close_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# def arrival_main_keyboard(role: str) -> InlineKeyboardMarkup:
#     """Главное меню для обработки приходов с учётом роли пользователя."""
#     buttons = [
#
#     ]
#
#     if role in [ADMIN, MANAGER, OPERATOR]:
#         buttons.append([InlineKeyboardButton(text="✅ Добавить приход", callback_data="add_arrival")])
#
#     # Только для менеджеров и администраторов добавляем кнопку "Приходы за месяц"
#     if role in [ADMIN, MANAGER]:
#         buttons.append([InlineKeyboardButton(text="📅 Приходы за месяц", callback_data="view_arrivals")])
#
#     buttons.append([InlineKeyboardButton(text="❌ Закрыть меню", callback_data="close_menu")])
#
#     return InlineKeyboardMarkup(inline_keyboard=buttons)
