from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.shipment import get_available_products


def shipment_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 Добавить отгрузку", callback_data="add_shipment"),
                InlineKeyboardButton(text="📦 Посмотреть отгрузки", callback_data="view_shipments"),
                InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")
            ]
        ]
    )

async def shipment_product_keyboard(session: AsyncSession):
    buttons = []
    products = await  get_available_products(session)
    for product, amount in products:
        buttons.append(
            [InlineKeyboardButton(
                text=f"{product.name}\n"
                     f" (остаток: {amount})",
                callback_data=f"product_{product.id}"
            )]
        )

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def shipment_add_more_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="add_more"),
                InlineKeyboardButton(text="❌ Нет", callback_data="finish_shipment")
            ]
        ]
    )
