from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.statistics import statistics_keyboard
from bot.models.database import async_session
from bot.services.shipment import get_shipments_for_current_month, get_shipments_for_period
from bot.services.statistics import (

    get_packed_month,
    get_packed_period,
    get_arrivals_month,
    get_arrivals_period,
    get_user_expenses,
    get_all_expenses
)
from bot.fsm.statistics import StatisticsStates
from bot.services.storage import get_raw_material_storage

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
    stock = await get_raw_material_storage(session)
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
async def packed_period_statistics(callback: CallbackQuery, state: FSMContext):
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


# Хендлер для получения суммы отгрузок за текущий месяц
@router.callback_query(F.data == "statistics:shipments_month")
async def get_shipments_this_month(callback_query: CallbackQuery, session: AsyncSession):
    """Получить сумму отгрузок за текущий месяц"""
    # Убедитесь, что сессия передается корректно
    if session is None:
        await callback_query.answer("Ошибка сессии.")
        return

    shipments = await get_shipments_for_current_month(session)

    if shipments:
        small_packs, large_packs = shipments
        total_packs = (small_packs or 0) + (large_packs or 0)
        await callback_query.message.answer(f"За текущий месяц отгружено:\n"
                                    f"Пачки по 3 кг: {small_packs or 0}\n"
                                    f"Пачки по 5 кг: {large_packs or 0}\n"
                                    f"Общее количество пачек: {total_packs}")
    else:
        await callback_query.message.answer("За текущий месяц нет отгрузок.")

@router.callback_query(F.data == "statistics:expenses_all")
async def all_expenses_statistics(callback: CallbackQuery, session: AsyncSession):
    expenses = await get_all_expenses(session)

    if not expenses:
        await callback.message.answer("❌ В базе данных пока нет расходов.")
        return

    text = "\n".join([f"👤 {item['user']}: 💰 {item['amount']} руб. ➝ {item['purpose']}" for item in expenses])
    await callback.message.answer(f"📜 *Список всех расходов:*\n{text}", parse_mode="Markdown")

router.callback_query(F.data == "statistics:shipments_period")
async def get_shipments_for_custom_period(callback: CallbackQuery):
    """Запрашиваем период отгрузок за конкретный интервал времени."""
    # Запросим у пользователя даты начала и конца периода
    await callback.message.answer("Введите период в формате: дд.мм.гггг - дд.мм.гггг")

@router.message(F.text)
async def handle_period_input(message: Message, session: AsyncSession, state: FSMContext):
    """Обрабатываем ввод периода пользователем."""
    period = message.text.strip()

    try:
        # Преобразуем строки в формат дат
        start_date_str, end_date_str = period.split(" - ")

        # Преобразуем в datetime
        start_date = datetime.strptime(start_date_str, "%d.%m.%Y")
        end_date = datetime.strptime(end_date_str, "%d.%m.%Y")

        # Получаем отгрузки за указанный период
        shipments = await get_shipments_for_period(session, start_date, end_date)

        if shipments:
            small_packs, large_packs = shipments
            total_packs = (small_packs or 0) + (large_packs or 0)
            await message.answer(f"Отгрузки за период с {start_date_str} по {end_date_str}:\n"
                                 f"Пачки по 3 кг: {small_packs or 0}\n"
                                 f"Пачки по 5 кг: {large_packs or 0}\n"
                                 f"Общее количество пачек: {total_packs}")
        else:
            await message.answer("В указанный период нет отгрузок.")

    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, используйте формат: дд.мм.гггг - дд.мм.гггг")
# Хендлер для кнопки "Закрыть меню"
@router.callback_query(F.data == "statistics:close")
async def close_shipment_menu(callback_query: CallbackQuery):
    """Закрытие меню отгрузки"""
    await callback_query.message.delete()
    await callback_query.answer()