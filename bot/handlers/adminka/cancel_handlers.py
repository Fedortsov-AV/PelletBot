# ------------------- Файл handlers/admin/cancel_handlers.py -------------------
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin import admin_menu
from bot.services.wrapers import admin_required

router = Router()


@router.callback_query(F.data == "cancel")
@admin_required
async def handle_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Обработка отмены операции"""
    await state.clear()
    await callback.message.answer(
        "Операция отменена",
        reply_markup=admin_menu()
    )
    await callback.answer()
