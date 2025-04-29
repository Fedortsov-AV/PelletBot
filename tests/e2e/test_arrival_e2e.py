import pytest
from aiogram import types
from datetime import datetime


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_arrival_flow(execute_handler, db_session, fake_update):
    from bot.handlers.arrival import (
        show_arrival_menu,
        add_arrival_handler,
        set_arrival_type,
        set_arrival_amount,
        confirm_arrival
    )

    # 1. Показываем меню
    fake_update.message.text = "Приходы"
    await execute_handler(show_arrival_menu, fake_update)

    # 2. Начинаем добавление прихода
    callback = types.CallbackQuery(
        id="1",
        from_user=fake_update.message.from_user,
        data="add_arrival",
        message=fake_update.message
    )
    await execute_handler(add_arrival_handler, callback)

    # 3. Выбираем тип продукции
    callback.data = "arrival_type:test_type"
    await execute_handler(set_arrival_type, callback)

    # 4. Указываем количество
    fake_update.message.text = "10"
    await execute_handler(set_arrival_amount, fake_update.message)

    # 5. Подтверждаем
    callback.data = "arrival_confirm"
    result = await execute_handler(confirm_arrival, callback)

    # Проверяем что приход создан в БД
    from bot.models.arrival import Arrival
    arrivals = await db_session.execute(select(Arrival))
    assert arrivals.scalars().first() is not None