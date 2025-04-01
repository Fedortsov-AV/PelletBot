from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models import RawProduct


def packaging_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Пропорция", callback_data="packaging_proportion")],
            [InlineKeyboardButton(text="✅ Расфасовано", callback_data="packaging_done")],
            [InlineKeyboardButton(text="❌ Закрыть меню", callback_data="close_menu")]
        ]
    )


async def raw_materials_keyboard(session: AsyncSession):
    """Клавиатура с выбором сырья для фасовки"""
    result = await session.execute(select(RawProduct))
    raw_products = result.scalars().all()

    buttons = []
    for product in raw_products:
        buttons.append([InlineKeyboardButton(
            text=product.name,
            callback_data=f"select_raw_{product.id}"
        )])

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_packaging")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)