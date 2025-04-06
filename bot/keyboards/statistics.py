from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def statistics_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="📦 Остатки", callback_data="statistics:stock")
    builder.button(text="🚚 Отгружено (мес)", callback_data="statistics:shipments_month")
    builder.button(text="📆 Отгружено (период)", callback_data="statistics:shipments_period")
    builder.button(text="📊 Фасовка (мес)", callback_data="statistics:packed_month")
    builder.button(text="📆 Фасовка (период)", callback_data="statistics:packed_period")
    builder.button(text="📥 Приходы (мес)", callback_data="statistics:arrivals_month")
    builder.button(text="📆 Приходы (период)", callback_data="statistics:arrivals_period")
    builder.button(text="💰 Мои расходы", callback_data="statistics:expenses_user")
    builder.button(text="📜 Все расходы", callback_data="statistics:expenses_all")
    builder.button(text="📋 Детали расходов", callback_data="statistics:expenses_detailed")
    builder.button(text="❌ Закрыть", callback_data="statistics:close")

    builder.adjust(2, 2, 2, 2, 2, 1)
    return builder.as_markup()