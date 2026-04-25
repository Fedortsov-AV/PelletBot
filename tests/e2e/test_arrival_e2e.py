import pytest
from aiogram import types, Bot, Dispatcher
from aiogram.types import Update, CallbackQuery, Message, Chat, User

from bot.constants.roles import MANAGER
from bot.fsm.arrival import ArrivalState
from bot.services.arrival import get_arrivals_for_month


# @pytest.mark.asyncio
# async def test_show_arrival_menu(dispatcher):
#     """Тест отображения меню 'Приходы'."""
#     from bot.handlers.arrival import router
#
#     # Убедимся, что роутер зарегистрирован
#     dispatcher.include_router(router)
#
#     # Создаем фейковое сообщение
#     fake_user = User(id=123, is_bot=False, first_name="Test", username="test_user")
#     fake_chat = Chat(id=1, type="private")
#
#     fake_message = Message(
#         message_id=1,
#         text="Приходы",
#         from_user=fake_user,
#         chat=fake_chat,
#         date=0  # Дата обязательна
#     )
#
#     update = types.Update(update_id=1, message=fake_message)
#
#     await dispatcher.feed_update(bot=dispatcher.bot, update=update)
#
#     # Проверяем, было ли отправлено сообщение
#     assert dispatcher.bot.send_message.called
#     sent_text = dispatcher.bot.send_message.call_args.kwargs["text"]
#     assert "Выберите действие:" in sent_text


@pytest.mark.asyncio
async def test_show_arrival_menu(dispatcher):
    """Тест отображения меню 'Приходы'."""
    from bot.handlers.arrival import router
    from tests.conftest import dispatcher as dispatcher_fixture

    # Получаем диспетчер из фикстуры
    dp = await anext(dispatcher)

    # Убедимся, что роутер зарегистрирован
    dp.include_router(router)

    # Создаем фейковое сообщение
    fake_user = User(id=123, is_bot=False, first_name="Test", username="test_user")
    fake_chat = Chat(id=1, type="private")

    fake_message = Message(
        message_id=1,
        text="Приходы",
        from_user=fake_user,
        chat=fake_chat,
        date=0  # Дата обязательна
    )

    update = types.Update(update_id=1, message=fake_message)

    await dp.feed_update(bot=dp.bot, update=update)

    # Проверяем, было ли отправлено сообщение
    assert dp.bot.send_message.called
    sent_text = dp.bot.send_message.call_args.kwargs["text"]
    assert "Выберите действие:" in sent_text

@pytest.mark.asyncio
async def test_add_arrival_flow(
    dispatcher,
    db_session,
    fake_callback_query,
    fake_message
):
    """Тест полного процесса добавления прихода."""
    test_arrival = None
    try:
        # Шаг 1: Открытие меню добавления
        fake_callback_query.data = "add_arrival"
        update = Update(update_id=1, callback_query=fake_callback_query)
        await dispatcher.feed_update(bot=dispatcher.bot, update=update)

        assert dispatcher.bot.send_message.called
        assert "Выберите тип продукции" in dispatcher.bot.send_message.call_args.kwargs["text"]

        # Сброс мока
        dispatcher.bot.send_message.reset_mock()

        # Шаг 2: Выбор типа (pellets)
        fake_callback_query.data = "arrival_type:pellets"
        update = Update(update_id=2, callback_query=fake_callback_query)
        await dispatcher.feed_update(bot=dispatcher.bot, update=update)

        assert fake_callback_query.message.edit_text.called
        assert "pellets" in fake_callback_query.message.edit_text.call_args.kwargs["text"]

        # Сброс мока
        fake_callback_query.message.edit_text.reset_mock()

        # Шаг 3: Ввод количества (150)
        fake_message.text = "150"
        update = Update(update_id=3, message=fake_message)
        await dispatcher.feed_update(bot=dispatcher.bot, update=update)

        assert dispatcher.bot.send_message.called
        assert "150 кг" in dispatcher.bot.send_message.call_args.kwargs["text"]

        # Сброс мока
        dispatcher.bot.send_message.reset_mock()

        # Шаг 4: Подтверждение
        fake_callback_query.data = "arrival_confirm"
        update = Update(update_id=4, callback_query=fake_callback_query)
        await dispatcher.feed_update(bot=dispatcher.bot, update=update)

        assert fake_callback_query.message.edit_text.called
        assert "успешно добавлен" in fake_callback_query.message.edit_text.call_args.kwargs["text"]

        # Проверка БД
        arrivals = await get_arrivals_for_month(db_session, fake_callback_query.from_user.id)
        assert len(arrivals) == 1
        assert arrivals[0].amount == 150
        test_arrival = arrivals[0]

    finally:
        if test_arrival:
            await db_session.delete(test_arrival)
            await db_session.commit()


@pytest.mark.asyncio
async def test_view_arrivals_handler(dispatcher, db_session, fake_callback_query):
    """Тест просмотра приходов за месяц."""
    from bot.services.arrival import add_arrival

    # Создаем приход вручную
    arrival = await add_arrival(db_session, fake_callback_query.from_user.id, "pellets", 100)
    await db_session.commit()

    # Вызываем handler
    fake_callback_query.data = "view_arrivals"
    update = Update(update_id=1, callback_query=fake_callback_query)
    await dispatcher.feed_update(bot=dispatcher.bot, update=update)

    assert dispatcher.bot.send_message.called
    messages = [call.kwargs["text"] for call in dispatcher.bot.send_message.call_args_list]
    assert any("pellets" in msg and "100 кг" in msg for msg in messages)


@pytest.mark.asyncio
async def test_delete_arrival_handler(dispatcher, db_session, fake_callback_query):
    """Тест удаления прихода."""
    from bot.services.arrival import add_arrival

    # Добавляем приход
    arrival = await add_arrival(db_session, fake_callback_query.from_user.id, "pellets", 100)
    await db_session.commit()

    # Удаляем
    fake_callback_query.data = f"delete_arrival:{arrival.id}"
    update = Update(update_id=1, callback_query=fake_callback_query)
    await dispatcher.feed_update(bot=dispatcher.bot, update=update)

    assert dispatcher.bot.send_message.called
    assert f"Приход {arrival.id} успешно удалён!" in dispatcher.bot.send_message.call_args.kwargs["text"]

    # Проверяем, что запись удалена
    arrivals = await get_arrivals_for_month(db_session, fake_callback_query.from_user.id)
    assert not any(a.id == arrival.id for a in arrivals)


@pytest.mark.asyncio
async def test_edit_arrival_flow(dispatcher, db_session, fake_callback_query, fake_message):
    """Тест редактирования прихода."""
    from bot.services.arrival import add_arrival

    # Добавляем приход
    arrival = await add_arrival(db_session, fake_callback_query.from_user.id, "pellets", 100)
    await db_session.commit()

    # Запускаем редактирование
    fake_callback_query.data = f"edit_arrival:{arrival.id}"
    update = Update(update_id=1, callback_query=fake_callback_query)
    await dispatcher.feed_update(bot=dispatcher.bot, update=update)

    assert dispatcher.bot.send_message.called
    assert "Введите новое количество (кг):" in dispatcher.bot.send_message.call_args.kwargs["text"]

    # Ввод нового количества
    fake_message.text = "200"
    update = Update(update_id=2, message=fake_message)
    await dispatcher.feed_update(bot=dispatcher.bot, update=update)

    # Выбор типа
    fake_callback_query.data = "arrival_type_edit:grains"
    update = Update(update_id=3, callback_query=fake_callback_query)
    await dispatcher.feed_update(bot=dispatcher.bot, update=update)

    assert dispatcher.bot.send_message.called
    assert "Количество прихода grains ID=" in dispatcher.bot.send_message.call_args.kwargs["text"]