from datetime import datetime
from typing import Dict

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.fsm.statistics import StatisticsStates
from bot.keyboards.statistics import statistics_keyboard
from bot.services.statistics import (
    get_stock_info,
    get_packaging_stats,
    get_arrivals_stats,
    get_user_expenses,
    get_all_expenses, get_detailed_expenses, get_shipments_period_stats, get_shipments_month_stats
)
from bot.services.user_service import get_user
from bot.services.wrapers import staff_required

router = Router()


def format_stock_info(stock_data: Dict) -> str:
    """Форматирует информацию о складе в читаемый текст"""
    text = "📦 Остатки на складе:\n"

    if stock_data.get("raw_materials"):
        text += "\n🧶 Сырье:\n"
        for name, amount in stock_data["raw_materials"].items():
            text += f"• {name}: {amount} кг\n"

    if stock_data.get("products"):
        text += "\n📦 Готовая продукция:\n"
        for name, amount in stock_data["products"].items():
            text += f"• {name}: {amount} шт.\n"

    if not stock_data.get("raw_materials") and not stock_data.get("products"):
        text += "\nℹ️ Данные о складе отсутствуют"

    return text


@router.message(F.text == "📊 Статистика")
@staff_required
async def show_statistics_menu(message: Message, session: AsyncSession):
    """Показывает меню статистики"""
    await message.answer(
        "Выберите нужный раздел статистики:",
        reply_markup=statistics_keyboard()
    )


@router.callback_query(F.data == "statistics:stock")
@staff_required
async def handle_stock_stats(callback: CallbackQuery, session: AsyncSession):
    """Обрабатывает запрос статистики остатков"""
    try:
        stock_data = await get_stock_info(session)
        response_text = format_stock_info(stock_data)
        await callback.message.answer(response_text, reply_markup=statistics_keyboard())
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при получении данных: {str(e)}")


@router.callback_query(F.data == "statistics:packed_month")
@staff_required
async def handle_packed_month(callback: CallbackQuery, session: AsyncSession):
    """Обрабатывает запрос статистики фасовки за месяц"""
    try:
        stats = await get_packaging_stats(session, period="month")
        await callback.message.answer(
            f"📊 Расфасовано за текущий месяц:\n"
            f"• Пачки 3кг: {stats['packs_3kg']} шт.\n"
            f"• Пачки 5кг: {stats['packs_5kg']} шт.",
            reply_markup=statistics_keyboard()
        )
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при получении данных: {str(e)}")


@router.callback_query(F.data == "statistics:packed_period")
@staff_required
async def start_packed_period(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Запрашивает период для статистики фасовки"""
    await callback.message.answer(
        "Введите период в формате ДД.ММ.ГГГГ - ДД.ММ.ГГГГ\n"
        "Например: 01.04.2025 - 30.04.2025"
    )
    await state.set_state(StatisticsStates.wait_packed_period)


@router.message(StatisticsStates.wait_packed_period)
@staff_required
async def process_packed_period(message: Message, state: FSMContext, session: AsyncSession):
    """Обрабатывает введенный период для статистики фасовки"""
    try:
        start_str, end_str = map(str.strip, message.text.split("-"))
        start_date = datetime.strptime(start_str, "%d.%m.%Y").date()
        end_date = datetime.strptime(end_str, "%d.%m.%Y").date()

        if start_date > end_date:
            raise ValueError("Начальная дата больше конечной")

        stats = await get_packaging_stats(
            session,
            period="custom",
            start_date=start_date,
            end_date=end_date
        )

        await message.answer(
            f"📆 Расфасовано за период {message.text}:\n"
            f"• Пачки 3кг: {stats['packs_3kg']} шт.\n"
            f"• Пачки 5кг: {stats['packs_5kg']} шт.",
            reply_markup=statistics_keyboard()
        )
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}\nПопробуйте снова.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при получении данных: {str(e)}")
    finally:
        await state.clear()


@router.callback_query(F.data == "statistics:arrivals_period")
@staff_required
async def start_arrivals_period(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Запрашивает период для статистики приходов"""
    await callback.message.answer(
        "Введите период для статистики приходов в формате ДД.ММ.ГГГГ - ДД.ММ.ГГГГ\n"
        "Например: 01.04.2025 - 30.04.2025"
    )
    await state.set_state(StatisticsStates.wait_arrivals_period)


@router.message(StatisticsStates.wait_arrivals_period)
@staff_required
async def process_arrivals_period(message: Message, state: FSMContext, session: AsyncSession):
    """Обрабатывает введенный период для статистики приходов"""
    try:
        start_str, end_str = map(str.strip, message.text.split("-"))
        start_date = datetime.strptime(start_str, "%d.%m.%Y").date()
        end_date = datetime.strptime(end_str, "%d.%m.%Y").date()

        if start_date > end_date:
            raise ValueError("Начальная дата больше конечной")

        arrivals = await get_arrivals_stats(
            session,
            period="custom",
            start_date=start_date,
            end_date=end_date
        )

        if not arrivals:
            await message.answer(f"📥 Нет данных о приходах за период {message.text}", reply_markup=statistics_keyboard())
            return

        response = f"📥 Приходы за период {message.text}:\n\n"
        for arrival_type, amount in arrivals.items():
            response += f"• {arrival_type}: {amount} кг\n"

        await message.answer(response, reply_markup=statistics_keyboard())
    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}\nПопробуйте снова.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при получении данных: {str(e)}")
    finally:
        await state.clear()


@router.callback_query(F.data == "statistics:arrivals_month")
@staff_required
async def handle_arrivals_month(callback: CallbackQuery, session: AsyncSession):
    """Обрабатывает запрос статистики приходов за месяц"""
    try:
        arrivals = await get_arrivals_stats(session, period="month")

        if not arrivals:
            await callback.message.answer("📥 Нет данных о приходах за текущий месяц", reply_markup=statistics_keyboard())
            return

        response = "📥 Приходы за текущий месяц:\n\n"
        for arrival_type, amount in arrivals.items():
            response += f"• {arrival_type}: {amount} кг\n"

        await callback.message.answer(response, reply_markup=statistics_keyboard())
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при получении данных: {str(e)}")


@router.callback_query(F.data == "statistics:expenses_user")
@staff_required
async def handle_user_expenses(callback: CallbackQuery, session: AsyncSession):
    """Обрабатывает запрос расходов пользователя"""
    try:
        user = await get_user(session, callback.from_user.id)
        total = await get_user_expenses(session, user.id)
        await callback.message.answer(
            f"💰 Ваши расходы из собственных средств: {total} руб.",
            reply_markup=statistics_keyboard()
        )
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при получении данных: {str(e)}")


@router.callback_query(F.data == "statistics:expenses_all")
@staff_required
async def handle_all_expenses(callback: CallbackQuery, session: AsyncSession):
    """Обрабатывает запрос всех расходов"""
    try:
        expenses = await get_all_expenses(session)

        if not expenses:
            await callback.message.answer("📜 Нет данных о расходах")
            return

        text = "📜 Последние расходы:\n\n"
        for expense in expenses[:10]:  # Ограничиваем 10 последними записями
            text += (
                f"👤 {expense['user']}\n"
                f"💰 {expense['amount']} руб. | {expense['date']}\n"
                f"📝 {expense['purpose']}\n\n"
            )

        await callback.message.answer(text, reply_markup=statistics_keyboard())
    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при получении данных: {str(e)}")


@router.callback_query(F.data == "statistics:expenses_detailed")
@staff_required
async def handle_detailed_expenses(callback: CallbackQuery, session: AsyncSession):
    """Обрабатывает запрос детализированного списка расходов"""
    try:
        expenses = await get_detailed_expenses(session)

        if not expenses:
            await callback.message.answer("📜 Нет данных о расходах")
            return

        # Разбиваем на сообщения по 5 записей, чтобы не превысить лимит длины
        for i in range(0, len(expenses), 5):
            batch = expenses[i:i + 5]
            response = "📜 Детализированные расходы:\n\n"

            for expense in batch:
                response += (
                    f"🔹 ID: {expense['id']}\n"
                    f"👤 Пользователь: {expense['user']}\n"
                    f"💰 Сумма: {expense['amount']} руб.\n"
                    f"📝 Назначение: {expense['purpose']}\n"
                    f"🏦 Источник: {expense['source']}\n"
                    f"📅 Дата: {expense['date']}\n\n"
                )

            await callback.message.answer(response, reply_markup=statistics_keyboard())

    except Exception as e:
        await callback.message.answer(f"⚠️ Ошибка при получении данных: {str(e)}")


@router.callback_query(F.data == "statistics:shipments_month")
@staff_required
async def handle_shipments_month(
        callback: CallbackQuery,
        session: AsyncSession
):
    """Обработка запроса статистики отгрузок за месяц"""
    await callback.answer()

    shipments = await get_shipments_month_stats(session)

    if not shipments:
        await callback.message.answer("Нет данных об отгрузках за текущий месяц.")
        return

    message_text = "📊 Отгружено за месяц:\n\n"
    for product_name, quantity in shipments:
        message_text += f"{product_name}: {quantity} шт.\n"

    await callback.message.answer(message_text, reply_markup=statistics_keyboard())


@router.callback_query(F.data == "statistics:shipments_period")
@staff_required
async def handle_shipments_period_start(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession
):
    """Запрос начальной даты периода для статистики отгрузок"""
    await callback.answer()
    await callback.message.answer("Введите начальную дату в формате ДД.ММ.ГГГГ:")
    await state.set_state(StatisticsStates.waiting_shipments_start_date)


@router.message(StatisticsStates.waiting_shipments_start_date)
@staff_required
async def handle_shipments_start_date(
        message: Message,
        state: FSMContext,
        session: AsyncSession
):
    """Обработка начальной даты периода"""
    try:
        start_date = datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(start_date=start_date)
        await message.answer("Введите конечную дату в формате ДД.ММ.ГГГГ:")
        await state.set_state(StatisticsStates.waiting_shipments_end_date)
    except ValueError:
        await message.answer("Неверный формат даты. Попробуйте снова.")


@router.message(StatisticsStates.waiting_shipments_end_date)
@staff_required
async def handle_shipments_end_date(
        message: Message,
        state: FSMContext,
        session: AsyncSession
):
    """Обработка конечной даты периода и вывод статистики"""
    try:
        end_date = datetime.strptime(message.text, "%d.%m.%Y")
        data = await state.get_data()
        start_date = data['start_date']

        shipments = await get_shipments_period_stats(session, start_date, end_date)

        if not shipments:
            await message.answer(
                f"Нет данных об отгрузках за период с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}.")
            return

        message_text = f"📊 Отгружено за период с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}:\n\n"
        for product_name, quantity in shipments:
            message_text += f"{product_name}: {quantity} шт.\n"

        await message.answer(message_text, reply_markup=statistics_keyboard())
        await state.clear()

    except ValueError:
        await message.answer("Неверный формат даты. Попробуйте снова.")

@router.callback_query(F.data == "statistics:close")
async def close_menu(callback: CallbackQuery):
    """Закрытие меню"""
    await callback.message.delete()
    await callback.answer()
