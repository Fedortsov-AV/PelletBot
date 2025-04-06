import asyncio

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.statistics import format_stock_info
from bot.services.statistics import get_stock_info


async def send_daily_stock_report(bot: Bot, session: AsyncSession):
    """Отправляет отчет об остатках с правильным управлением сессией"""
    try:
        from bot.services.db_service import get_admin_ids

        # Получаем данные внутри активной сессии
        stock_data = await get_stock_info(session)
        admin_ids = await get_admin_ids(session)

        if not admin_ids:
            print("Нет администраторов для отправки отчета")
            return

        report_text = await _format_daily_report(stock_data)

        for admin_id in admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    report_text,
                    parse_mode="HTML"
                )
                await asyncio.sleep(0.3)  # Защита от флуда
            except Exception as e:
                print(f"Ошибка отправки admin {admin_id}: {str(e)}")

    except Exception as e:
        print(f"Ошибка формирования отчета: {str(e)}")
        raise


async def _format_daily_report(stock_data: dict) -> str:
    """Форматирование отчета с датой"""
    from datetime import datetime
    date_str = datetime.now().strftime("%d.%m.%Y")

    text = (
        f"📅 <b>Ежедневный отчет на {date_str}</b>\n\n"
        f"{format_stock_info(stock_data)}\n"
        f"📊 <b>Итого:</b>\n"
        f"├ Сырьё: <b>{sum(stock_data.get('raw_materials', {}).values())} кг</b>\n"
        f"└ Продукция: <b>{sum(stock_data.get('products', {}).values())} шт.</b>"
    )
    return text
