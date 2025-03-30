from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.statistics import statistics_keyboard
from bot.services.statistics import (

    get_packed_month,
    get_packed_period,
    get_arrivals_month,
    get_arrivals_period,
    get_user_expenses,
    get_all_expenses
)
from bot.fsm.statistics import StatisticsStates
from bot.services.storage import get_stock

router = Router()

# 📊 Хендлер нажатия на кнопку "Статистика"
@router.message(F.text == "📊 Статистика")
async def statistics_menu(message: Message):
    await message.answer("Выберите нужный раздел статистики:", reply_markup=statistics_keyboard())

# Открытие меню статистики
@router.callback_query(F.data == "statistics")
async def open_statistics_menu(callback: CallbackQuery):
    await callback.message.edit_text("Выберите нужную статистику:", reply_markup=statistics_keyboard())

# Остатки на складе
@router.callback_query(F.data == "statistics:stock")
async def stock_statistics(callback: CallbackQuery, session: AsyncSession):
    stock = await get_stock(session)
    await callback.message.answer(
        f"Сейчас на складе:\n"
        f"- {stock.pellets_6mm} кг пеллет по 6мм\n"
        f"- {stock.packs_3kg} пачек по 3 кг\n"
        f"- {stock.packs_5kg} пачек по 5 кг"
    )

# Расфасовано за месяц
@router.callback_query(F.data == "statistics:packed_month")
async def packed_month_statistics(callback: CallbackQuery, session: AsyncSession):
    result = await get_packed_month(session)
    await callback.message.answer(
        f"За текущий месяц расфасовано:\n"
        f"- {result['packs_3kg']} пачек по 3 кг\n"
        f"- {result['packs_5kg']} пачек по 5 кг"
    )

# Расфасовано за период
@router.callback_query(F.data == "statistics:packed_period")
async def packed_period_statistics(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.message.answer("Введите период в формате ДД.ММ.ГГГГ - ДД.ММ.ГГГГ:")
    await state.set_state(StatisticsStates.select_period_packed)

@router.message(StatisticsStates.select_period_packed)
async def get_packed_period_statistics(message: Message, state: FSMContext, session: AsyncSession):
    try:
        start_date, end_date = map(str.strip, message.text.split("-"))
        start_date = datetime.strptime(start_date, "%d.%m.%Y")
        end_date = datetime.strptime(end_date, "%d.%m.%Y")

        result = await get_packed_period(session, start_date, end_date)
        await message.answer(
            f"За период {message.text} расфасовано:\n"
            f"- {result['packs_3kg']} пачек по 3 кг\n"
            f"- {result['packs_5kg']} пачек по 5 кг"
        )
    except ValueError:
        await message.answer("Некорректный формат даты! Попробуйте снова.")
    finally:
        await state.clear()

# Сумма приходов за месяц
@router.callback_query(F.data == "statistics:arrivals_month")
async def arrivals_month_statistics(callback: CallbackQuery, session: AsyncSession):
    total_arrivals = await get_arrivals_month(session)
    await callback.message.answer(f"Приход за текущий месяц составляет {total_arrivals} кг.")

# Сумма приходов за период
@router.callback_query(F.data == "statistics:arrivals_period")
async def arrivals_period_statistics(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите период в формате ДД.ММ.ГГГГ - ДД.ММ.ГГГГ:")
    await state.set_state(StatisticsStates.select_period_arrivals)

@router.message(StatisticsStates.select_period_arrivals)
async def get_arrivals_period_statistics(message: Message, state: FSMContext, session: AsyncSession):
    try:
        start_date, end_date = map(str.strip, message.text.split("-"))
        start_date = datetime.strptime(start_date, "%d.%m.%Y")
        end_date = datetime.strptime(end_date, "%d.%m.%Y")

        total_arrivals = await get_arrivals_period(session, start_date, end_date)
        await message.answer(f"Приход за {message.text} составляет {total_arrivals} кг.")
    except ValueError:
        await message.answer("Некорректный формат даты! Попробуйте снова.")
    finally:
        await state.clear()

# Расходы пользователя
@router.callback_query(F.data == "statistics:expenses_user")
async def user_expenses_statistics(callback: CallbackQuery, session: AsyncSession):
    total_expenses = await get_user_expenses(session, callback.from_user.id)
    await callback.message.answer(f"Ваши расходы из собственных средств составляют {total_expenses} руб.")

@router.callback_query(F.data == "statistics:expenses_all")
async def all_expenses_statistics(callback: CallbackQuery, session: AsyncSession):
    expenses = await get_all_expenses(session)

    if not expenses:
        await callback.message.answer("❌ В базе данных пока нет расходов.")
        return

    text = "\n".join([f"👤 {item['user']}: 💰 {item['amount']} руб. ➝ {item['purpose']}" for item in expenses])
    await callback.message.answer(f"📜 *Список всех расходов:*\n{text}", parse_mode="Markdown")

# Хендлер для кнопки "Закрыть меню"
@router.callback_query(F.data == "statistics:close")
async def close_shipment_menu(callback_query: CallbackQuery):
    """Закрытие меню отгрузки"""
    await callback_query.message.delete()
    await callback_query.answer()