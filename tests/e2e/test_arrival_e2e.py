from unittest.mock import AsyncMock

import pytest
from aiogram import types, Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.methods import SendMessage, EditMessageText
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.arrival import get_arrivals_for_month, get_arrival_by_id

import pytest
from aiogram import types
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_full_arrival_flow(
        dispatcher: Dispatcher,  # Теперь получаем объект Dispatcher
        db_session: AsyncSession,
        fake_callback: types.CallbackQuery,
        fake_message: types.Message,
):
    # 1. Имитируем нажатие кнопки "Добавить приход"
    fake_callback.data = "add_arrival"
    await dispatcher.feed_update(
        bot=dispatcher.bot,
        update=types.Update(
            update_id=1,
            callback_query=fake_callback
        )
    )

    # Проверка: отправлено сообщение с выбором типа продукции
    assert dispatcher.bot.send_message.await_args[1]["text"] == "Выберите тип продукции:"

    # 2. Выбираем тип "pellets"
    fake_callback.data = "arrival_type:pellets"
    await dispatcher.feed_update(
        bot=dispatcher.bot,
        update=types.Update(
            update_id=2,
            callback_query=fake_callback
        )
    )

    # Проверка: сообщение обновлено
    assert "pellets" in dispatcher.bot.edit_message_text.await_args[1]["text"]

    # 3. Вводим количество
    fake_message.text = "150"
    await dispatcher.feed_update(
        bot=dispatcher.bot,
        update=types.Update(
            update_id=3,
            message=fake_message
        )
    )

    # Проверка: подтверждение прихода
    assert "150 кг" in dispatcher.bot.send_message.await_args[1]["text"]

    # 4. Подтверждаем приход
    fake_callback.data = "arrival_confirm"
    await dispatcher.feed_update(
        bot=dispatcher.bot,
        update=types.Update(
            update_id=4,
            callback_query=fake_callback
        )
    )

    # Проверка: финальное сообщение
    assert "успешно добавлен" in dispatcher.bot.edit_message_text.await_args[1]["text"]


@pytest.mark.asyncio
async def test_view_and_delete_arrival(
        dispatcher: Dispatcher,
        db_session: AsyncSession,
        fake_callback: CallbackQuery
):
    # Тест: Просмотр и удаление прихода
    # Добавляем тестовый приход
    fake_callback.data = "view_arrivals"

    await dispatcher.feed_update(
        bot=dispatcher.bot,
        update=types.Update(
            update_id=1,
            callback_query=fake_callback
        )
    )

    # Проверка отображения приходов
    if dispatcher.bot.send_message.await_args:
        assert "Приходы за этот месяц отсутствуют" in dispatcher.bot.send_message.await_args[1]['text']
    else:
        assert "кг" in dispatcher.bot.send_message.await_args[1]['text']

    # Удаление прихода (если есть)
    arrivals = await get_arrivals_for_month(db_session, fake_callback.from_user.id)
    if arrivals:
        arrival = arrivals[0]
        fake_callback.data = f"delete_arrival:{arrival.id}"

        await dispatcher.feed_update(
            bot=dispatcher.bot,
            update=types.Update(
                update_id=2,
                callback_query=fake_callback
            )
        )

        # Проверка сообщения об удалении
        assert f"успешно удалён" in dispatcher.bot.send_message.await_args[1]['text']


@pytest.mark.asyncio
async def test_arrival_edit_flow(
        dispatcher: Dispatcher,
        db_session: AsyncSession,
        fake_callback: CallbackQuery,
        fake_message: Message
):
    # Тест: Редактирование прихода
    # 1. Инициализация редактирования
    fake_callback.data = "edit_arrival:1"
    await dispatcher.feed_update(
        bot=dispatcher.bot,
        update=types.Update(
            update_id=1,
            callback_query=fake_callback
        )
    )

    # Проверка запроса нового количества
    assert "Введите новое количество" in dispatcher.bot.send_message.await_args[1]['text']

    # 2. Ввод нового количества
    fake_message.text = "200"
    await dispatcher.feed_update(
        bot=dispatcher.bot,
        update=types.Update(
            update_id=2,
            message=fake_message
        )
    )

    # Проверка выбора типа
    assert "Выберите тип продукции" in dispatcher.bot.send_message.await_args[1]['text']

    # 3. Выбор нового типа
    fake_callback.data = "arrival_type_edit:new_type"
    await dispatcher.feed_update(
        bot=dispatcher.bot,
        update=types.Update(
            update_id=3,
            callback_query=fake_callback
        )
    )

    # Проверка финального сообщения
    assert "изменено на 200" in dispatcher.bot.send_message.await_args[1]['text']

    # Проверка изменений в БД
    arrival = await get_arrival_by_id(db_session, 1)
    assert arrival.amount == 200
    assert arrival.type == "new_type"