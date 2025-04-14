from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.fsm.packaging import PackagingStates
from bot.keyboards.packaging import packaging_main_keyboard, raw_materials_keyboard
from bot.models import Product
from bot.services.packaging_service import calculate_packaging_ratio, get_raw_materials, \
    get_products_for_raw_material, save_packaging, update_stock_after_packaging, get_raw_material_availability
from bot.services.user_service import get_user
from bot.services.wrapers import restrict_anonymous

router = Router()


@router.message(F.text == "📦 Фасовка")
@restrict_anonymous
async def show_packaging_menu(message: Message, session: AsyncSession):
    """Открывает меню фасовки"""
    await message.answer("Выберите действие:", reply_markup=packaging_main_keyboard())


@router.callback_query(F.data == "packaging_proportion")
@restrict_anonymous
async def start_packaging_proportion(
        callback: CallbackQuery,
        session: AsyncSession,
        state: FSMContext
):
    """Начало процесса расчета пропорции - выбор сырья"""
    keyboard = await raw_materials_keyboard(session)
    await callback.message.answer(
        "Выберите сырье для фасовки:",
        reply_markup=keyboard
    )
    await state.set_state(PackagingStates.waiting_for_raw_material)


@router.callback_query(
    PackagingStates.waiting_for_raw_material,
    F.data.startswith("select_raw_")
)
@restrict_anonymous
async def select_raw_material(
        callback: CallbackQuery,
        session: AsyncSession,
        state: FSMContext
):
    """Обработка выбора сырья и запрос пропорции"""
    raw_product_id = int(callback.data.split("_")[-1])

    # Получаем информацию о сырье
    raw_materials = await get_raw_materials(session)
    raw_product = next((rp for rp, amt in raw_materials if rp.id == raw_product_id), None)

    if not raw_product:
        await callback.message.answer("Сырье не найдено!")
        await state.clear()
        return

    # Получаем продукты из этого сырья
    products = await get_products_for_raw_material(session, raw_product_id)
    if len(products) != 2:
        await callback.message.answer(
            "Для данного сырья должно быть ровно 2 вида продукции!"
        )
        await state.clear()
        return

    product_names = [p.name for p, _ in products]

    await state.update_data(
        raw_product_id=raw_product_id,
        product_names=product_names
    )
    await state.set_state(PackagingStates.waiting_for_ratio)
    await callback.message.answer(
        f"Продукция для фасовки: {product_names[0]} и {product_names[1]}\n"
        f"Введите соотношение фасовки в формате X/Y (например 2/1):"
    )


@router.message(PackagingStates.waiting_for_ratio)
@restrict_anonymous
async def process_ratio(
        message: Message,
        session: AsyncSession,
        state: FSMContext
):
    """Обработка введенной пропорции и вывод результата"""
    data = await state.get_data()
    raw_product_id = data["raw_product_id"]
    product_names = data["product_names"]

    # Получаем остаток сырья
    raw_materials = await get_raw_materials(session)
    raw_amount = next((amt for rp, amt in raw_materials if rp.id == raw_product_id), 0)

    if raw_amount <= 0:
        await message.answer("На складе нет данного сырья!")
        await state.clear()
        return

    # Рассчитываем пропорцию
    result, error = await calculate_packaging_ratio(
        session,
        raw_product_id,
        message.text,
        raw_amount
    )

    if error:
        await message.answer(error)
        return

    await message.answer(
        f"Для расфасовки в соответствии с пропорцией {message.text}:\n"
        f"🔹 {product_names[0]} - {result[product_names[0]]} пачек\n"
        f"🔹 {product_names[1]} - {result[product_names[1]]} пачек\n\n"
        f"Будет использовано {result['used_raw']} кг сырья"
    )
    await state.clear()


@router.callback_query(F.data == "packaging_done")
@restrict_anonymous
async def start_packaging_done(
        callback: CallbackQuery,
        session: AsyncSession,
        state: FSMContext
):
    """Начало процесса учета расфасованной продукции"""
    keyboard = await raw_materials_keyboard(session)
    await callback.message.answer(
        "Выберите сырье, которое было расфасовано:",
        reply_markup=keyboard
    )
    await state.set_state(PackagingStates.waiting_for_done_raw_material)


@router.callback_query(
    PackagingStates.waiting_for_done_raw_material,
    F.data.startswith("select_raw_")
)
@restrict_anonymous
async def select_packaging_raw_material(
        callback: CallbackQuery,
        session: AsyncSession,
        state: FSMContext
):
    """Обработка выбора сырья и запрос продукта"""
    raw_product_id = int(callback.data.split("_")[-1])

    # Получаем продукты из этого сырья
    products = await get_products_for_raw_material(session, raw_product_id)
    if not products:
        await callback.message.answer("Для данного сырья нет продукции!")
        await state.clear()
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                                        [InlineKeyboardButton(text=p.name,
                                                                              callback_data=f"select_product_{p.id}")]
                                                        for p, _ in products
                                                    ] + [[InlineKeyboardButton(text="❌ Отмена",
                                                                               callback_data="cancel_packaging")]])

    await state.update_data(raw_product_id=raw_product_id)
    await state.set_state(PackagingStates.waiting_for_product)
    await callback.message.answer(
        "Выберите продукт, который был расфасован:",
        reply_markup=keyboard
    )


@router.callback_query(
    PackagingStates.waiting_for_product,
    F.data.startswith("select_product_")
)
@restrict_anonymous
async def select_packaging_product(
        callback: CallbackQuery,
        state: FSMContext,
        session: AsyncSession
):
    """Обработка выбора продукта и запрос количества"""
    product_id = int(callback.data.split("_")[-1])
    await state.update_data(product_id=product_id)
    await state.set_state(PackagingStates.waiting_for_amount)
    await callback.message.answer("Введите количество расфасованных пачек:")


@router.message(PackagingStates.waiting_for_amount)
@restrict_anonymous
async def process_packaging_amount(
        message: Message,
        state: FSMContext,
        session: AsyncSession
):
    """Обработка количества пачек и сохранение фасовки"""
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError

        data = await state.get_data()
        product = await session.get(Product, data['product_id'])
        required_raw = amount * product.weight

        # Получаем информацию о доступности сырья
        current_amount, is_available, max_packs = await get_raw_material_availability(
            session,
            data['raw_product_id'],
            product_weight=product.weight,
            required_amount=required_raw
        )

        if not is_available:
            await message.answer(
                f"❌ Недостаточно сырья на складе!\n"
                f"Требуется: {required_raw} кг\n"
                f"Доступно: {current_amount} кг\n"
                f"Максимально можно расфасовать: {max_packs} пачек по {product.weight} кг"
            )
            return

        user_id = await get_user(session, message.from_user.id)
        print(user_id)
        # Дальнейшая обработка фасовки...
        packaging = await save_packaging(
            session,
            user_id.id,
            product.id,
            product.raw_product_id,
            amount,
            required_raw)
        await update_stock_after_packaging(session, product.id, product.raw_product_id, amount, required_raw)

        await message.answer("Фасовка добавлена")
        await state.clear()

    except ValueError:
        await message.answer("Введите корректное количество (целое положительное число).")
