from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from bot.keyboards.packaging import packaging_main_keyboard
from bot.services.packaging_service import get_current_stock, save_packaging
from bot.fsm.packaging import PackagingStates

router = Router()

@router.message(F.text == "📦 Фасовка")
async def show_packaging_menu(message: Message):
    """Открывает меню фасовки"""
    await message.answer("Выберите действие:", reply_markup=packaging_main_keyboard())

@router.callback_query(F.data == "packaging_proportion")
async def show_packaging_proportion(callback: CallbackQuery, session: AsyncSession):
    """Показываем, сколько нужно расфасовать"""
    total_stock = await get_current_stock(session)

    # Допустим, у нас соотношение 2:1 (2 пачки по 3 кг на 1 пачку по 5 кг)
    small_packs = (total_stock // 8) * 2
    large_packs = (total_stock // 8)

    await callback.message.answer(
        f"Необходимо расфасовать {small_packs} пачек по 3кг и {large_packs} пачек по 5кг"
    )


@router.callback_query(F.data == "packaging_done")
async def start_packaging(callback: CallbackQuery, state: FSMContext):
    """Запрашиваем количество расфасованных пачек"""
    await state.set_state(PackagingStates.waiting_for_small_packs)
    await callback.message.answer("Введите количество пачек по 3кг:")


@router.message(PackagingStates.waiting_for_small_packs)
async def get_small_packs(message: Message, state: FSMContext):
    """Сохраняем количество 3кг пачек"""
    await state.update_data(small_packs=int(message.text))
    await state.set_state(PackagingStates.waiting_for_large_packs)
    await message.answer("Введите количество пачек по 5кг:")


@router.message(PackagingStates.waiting_for_large_packs)
async def get_large_packs(message: Message, state: FSMContext, session: AsyncSession):
    """Сохраняем данные, записываем в БД"""
    data = await state.get_data()
    small_packs = data["small_packs"]
    large_packs = int(message.text)
    used_raw = small_packs * 3 + large_packs * 5  # Расход первичной продукции

    await save_packaging(session, message.from_user.id, small_packs, large_packs, used_raw)

    await message.answer(f"Фасовка завершена. Записано:\n"
                         f"🔹 {small_packs} пачек по 3 кг\n"
                         f"🔹 {large_packs} пачек по 5 кг\n"
                         f"📉 Израсходовано: {used_raw} кг")
    await state.clear()


@router.callback_query(F.data == "set_packaging_ratio")
async def ask_for_ratio(callback: CallbackQuery, state: FSMContext):
    """Запрашиваем соотношение упаковки"""
    await state.set_state(PackagingStates.waiting_for_ratio)
    await callback.message.answer("Введите соотношение пачек по 3кг и 5кг в формате X/Y:")


@router.message(PackagingStates.waiting_for_ratio)
async def save_ratio(message: Message, state: FSMContext):
    """Сохраняем новое соотношение"""
    try:
        small, large = map(int, message.text.split('/'))
        # Тут можно сохранить соотношение в БД
        await message.answer(f"Новое соотношение установлено: {small} пачек по 3кг на {large} пачек по 5кг")
        await state.clear()
    except ValueError:
        await message.answer("Ошибка! Введите корректное соотношение в формате X/Y")
