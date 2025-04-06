from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.stock_handlers import send_daily_stock_report

# from bot.keyboards.user import user_menu

router = Router()


@router.message(Command("test_report"))
async def test_report(message: Message, session: AsyncSession):
    """Ручная проверка отчета"""
    await send_daily_stock_report(message.bot, session)
