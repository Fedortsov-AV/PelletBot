# ------------------- Файл handlers/admin/cancel_handlers.py -------------------
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.admin import admin_menu

router = Router()


@router.callback_query(F.data == "cancel")
async def handle_cancel(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены операции"""
    await state.clear()
    await callback.message.answer(
        "Операция отменена",
        reply_markup=admin_menu()
    )
    await callback.answer()
