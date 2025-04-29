import pytest
from aiogram import types
from aiogram.fsm.storage.memory import MemoryStorage

from bot.fsm.arrival import ArrivalState


@pytest.mark.asyncio
async def test_arrival_flow(dispatcher, bot, db_session, fake_user):
    from bot.handlers.arrival import router

    # Имитируем нажатие кнопки "Приходы"
    msg = types.Message(
        message_id=1,
        from_user=fake_user,
        chat=types.Chat(id=1, type="private"),
        text="Приходы",
        date=None
    )
    await dispatcher.feed_update(bot, msg)

    # Проверяем ответ бота
    last_message = bot.send_message.call_args[0][1]
    assert "Выберите действие" in last_message

    # Имитируем выбор "Добавить приход"
    callback = types.CallbackQuery(
        id="1",
        from_user=fake_user,
        data="add_arrival",
        message=msg
    )
    await dispatcher.feed_update(bot, callback)

    # Проверяем что бот запросил тип продукции
    assert "Выберите тип продукции" in bot.send_message.call_args[0][1]