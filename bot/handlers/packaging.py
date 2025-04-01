from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.packaging import packaging_main_keyboard
from bot.services.packaging_service import save_packaging
from bot.services.storage import update_stock_packaging, get_raw_material_storage
from bot.fsm.packaging import PackagingStates

router = Router()


@router.message(F.text == "📦 Фасовка")
async def show_packaging_menu(message: Message):
    """Открывает меню фасовки"""
    await message.answer("Выберите действие:", reply_markup=packaging_main_keyboard())


@router.callback_query(F.data == "packaging_proportion")
async def show_packaging_proportion(callback: CallbackQuery, session: AsyncSession):
    """Показываем, сколько нужно расфасовать"""
    stock = await get_raw_material_storage(session)

    if stock.amount < 8:
        await callback.message.answer("На складе недостаточно пеллет для фасовки.")
        return

    # Соотношение 2:1 (по умолчанию)
    small_packs = (stock.pellets_6mm // 8) * 2
    large_packs = (stock.pellets_6mm // 8)

    await callback.message.answer(
        f"Необходимо расфасовать {small_packs} пачек по 3 кг и {large_packs} пачек по 5 кг"
    )


@router.callback_query(F.data == "packaging_done")
async def start_packaging(callback: CallbackQuery, state: FSMContext):
    """Запрашиваем количество расфасованных пачек"""
    await state.set_state(PackagingStates.waiting_for_small_packs)
    await callback.message.answer("Введите количество пачек по 3 кг:")


@router.message(PackagingStates.waiting_for_small_packs)
async def get_small_packs(message: Message, state: FSMContext):
    """Сохраняем количество 3кг пачек"""
    try:
        small_packs = int(message.text)
        if small_packs < 0:
            raise ValueError
        await state.update_data(small_packs=small_packs)
        await state.set_state(PackagingStates.waiting_for_large_packs)
        await message.answer("Введите количество пачек по 5 кг:")
    except ValueError:
        await message.answer("Введите корректное количество (целое положительное число).")


@router.message(PackagingStates.waiting_for_large_packs)
async def get_large_packs(message: Message, state: FSMContext, session: AsyncSession):
    """Сохраняем данные, записываем в БД"""
    try:
        large_packs = int(message.text)
        if large_packs < 0:
            raise ValueError

        data = await state.get_data()
        small_packs = data["small_packs"]
        used_raw = small_packs * 3 + large_packs * 5  # Расход первичной продукции

        # Проверяем наличие пеллет
        stock = await get_raw_material_storage(session)
        if stock.pellets_6mm < used_raw:
            await message.answer("Недостаточно пеллет на складе для фасовки!")
            await state.clear()
            return

        # Обновляем склад и сохраняем фасовку
        await update_stock_packaging(session, used_raw, small_packs, large_packs)
        await save_packaging(session, message.from_user.id, small_packs, large_packs, used_raw)

        await message.answer(
            f"✅ Фасовка завершена:\n"
            f"🔹 {small_packs} пачек по 3 кг\n"
            f"🔹 {large_packs} пачек по 5 кг\n"
            f"📉 Израсходовано: {used_raw} кг"
        )
        await state.clear()
    except ValueError:
        await message.answer("Введите корректное количество (целое положительное число).")


@router.callback_query(F.data == "set_packaging_ratio")
async def ask_for_ratio(callback: CallbackQuery, state: FSMContext):
    """Запрашиваем соотношение упаковки"""
    await state.set_state(PackagingStates.waiting_for_ratio)
    await callback.message.answer("Введите соотношение пачек по 3 кг и 5 кг в формате X/Y:")


@router.message(PackagingStates.waiting_for_ratio)
async def save_ratio(message: Message, state: FSMContext):
    """Сохраняем новое соотношение"""
    try:
        small, large = map(int, message.text.split('/'))
        if small <= 0 or large <= 0:
            raise ValueError
        # Тут можно сохранить соотношение в БД
        await message.answer(f"✅ Новое соотношение установлено: {small} пачек по 3 кг на {large} пачек по 5 кг")
        await state.clear()
    except ValueError:
        await message.answer("Ошибка! Введите корректное соотношение в формате X/Y (например, 2/1).")


@router.callback_query(F.data == "close_menu")
async def close_menu(callback: CallbackQuery):
    """ Закрывает админское меню. """
    await callback.message.delete()
    await callback.answer()