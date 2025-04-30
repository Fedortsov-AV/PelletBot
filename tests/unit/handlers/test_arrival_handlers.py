import pytest
from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.fsm.context import FSMContext

from bot.fsm.arrival import ArrivalState
from bot.handlers.arrival import show_arrival_menu, set_arrival_amount, set_arrival_type, add_arrival_handler, \
    confirm_arrival, cancel_arrival
from bot.keyboards.arrival import arrival_main_keyboard

import pytest
from bot.handlers.arrival import show_arrival_menu
from bot.keyboards.arrival import arrival_main_keyboard
from unittest.mock import AsyncMock, MagicMock, ANY


@pytest.mark.asyncio
async def test_show_arrival_menu_user_exists(fake_message, fake_user, mocker):
    # Создаем мок сессии
    session = AsyncMock()

    # Мокаем ответ от session.execute()
    execute_result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.first.return_value = fake_user(1, 123, "test", "manager")
    execute_result.scalars.return_value = scalars_mock
    session.execute.return_value = execute_result

    # Мокаем функцию get_user (если нужно)
    mocker.patch("bot.handlers.arrival.get_user", return_value=fake_user(1, 123, "test", "manager"))

    # Вызываем хендлер
    await show_arrival_menu(fake_message, session=session)

@pytest.mark.asyncio
async def test_show_arrival_menu_user_not_exists(fake_message, mocker):
    # Убираем анонимность (декоратор проверяет БД, а не флаг Telegram)
    fake_message.from_user.is_anonymous = False  # <-- Важно!
    fake_message.from_user.id = 123  # Любой ID
    fake_message.from_user.full_name = "Test User"

    # Мокаем get_or_create_user для возврата "anonymous"
    mocker.patch(
        "bot.services.wrapers.get_or_create_user",
        AsyncMock(return_value=MagicMock(role="anonymous"))
    )

    # Мокаем сессию
    session = AsyncMock()

    # Ожидаем CancelHandler
    with pytest.raises(CancelHandler):
        await show_arrival_menu(fake_message, session=session)

    # Проверяем сообщение о неверифицированном аккаунте
    fake_message.answer.assert_called_once_with(
        "❌ Ваш аккаунт не верифицирован. Обратитесь к администратору."
    )
@pytest.mark.asyncio
async def test_add_arrival_handler(fake_callback, mock_db_session, mocker, mock_state):
    """Тест инициализации добавления прихода"""
    # Мокаем зависимости
    mocker.patch("bot.handlers.arrival.arrival_types_keyboard", AsyncMock(return_value=MagicMock()))
    mocker.patch("bot.services.user_service.get_user", AsyncMock(return_value=MagicMock(role="manager")))

    # Вызываем хэндлер с корректным mock_state
    await add_arrival_handler(fake_callback, state=mock_state, session=mock_db_session)

    # Проверяем отправку сообщения с клавиатурой
    fake_callback.message.answer.assert_called_once_with(
        "Выберите тип продукции:",
        reply_markup=ANY
    )

    # Проверяем установку состояния FSM
    mock_state.set_state.assert_awaited_once_with(ArrivalState.type)


@pytest.mark.asyncio
async def test_set_arrival_type(fake_callback, mock_state):
    """Тест выбора типа продукции"""
    await set_arrival_type(fake_callback, mock_state)

    mock_state.set_state.assert_called_with(ArrivalState.amount)
    fake_callback.message.edit_text.assert_called_with(
        "Вы выбрали: pellets\nВведите количество (кг):"
    )


@pytest.mark.asyncio
async def test_set_arrival_amount_valid(mock_state, fake_message):
    """Тест ввода корректного количества"""
    fake_message.text = "50"
    await set_arrival_amount(fake_message, mock_state)

    mock_state.update_data.assert_called_with(amount=50)
    fake_message.answer.assert_called_once()
    mock_state.set_state.assert_called_with(ArrivalState.confirm)


@pytest.mark.asyncio
async def test_confirm_arrival(mock_db_session, fake_callback, mock_state, mocker):
    """Тест подтверждения прихода"""
    test_data = {"type": "pellets", "amount": 100}
    mock_state.get_data.return_value = test_data

    # Мокаем add_arrival с эмуляцией коммита
    async def mock_add_arrival(session, *args, **kwargs):
        await session.commit()  # Эмулируем коммит внутри мока
        return MagicMock(id=1)

    mocker.patch(
        "bot.handlers.arrival.add_arrival",
        new_callable=AsyncMock,
        side_effect=mock_add_arrival
    )

    await confirm_arrival(fake_callback, mock_state, mock_db_session)

    # Проверяем вызовы
    mock_db_session.commit.assert_awaited_once()
    fake_callback.message.edit_text.assert_awaited_with("✅ Приход успешно добавлен!")
    mock_state.clear.assert_awaited_once()
# #
# @pytest.mark.asyncio
# async def test_add_arrival_handler(fake_callback, mocker):
#     session = AsyncMock()
#     state = AsyncMock()
#
#     # Мокаем пользователя
#     mocker.patch(
#         "bot.services.wrapers.get_or_create_user",
#         return_value=MagicMock(role="manager")
#     )
#
#     # Мокаем клавиатуру
#     mock_keyboard = MagicMock()
#     mocker.patch("bot.handlers.arrival.arrival_types_keyboard", return_value=mock_keyboard)
#
#     await add_arrival_handler(fake_callback, state=state, session=session)
#
#     fake_callback.message.answer.assert_called_once_with()
#
#
#
# @pytest.mark.asyncio
# async def test_set_arrival_type_sets_type_and_asks_amount(fake_callback):
#     state = AsyncMock()
#     fake_callback.data = "arrival_type:pellets"
#
#     await set_arrival_type(fake_callback, state)
#
#     state.update_data.assert_awaited_once_with(type="pellets")
#     fake_callback.message.edit_text.assert_awaited_once_with(
#         "Вы выбрали: pellets\nВведите количество (кг):"
#     )
#     state.set_state.assert_awaited_once_with(ArrivalState.amount)
#
#
# @pytest.mark.asyncio
# async def test_set_arrival_amount_valid_number(fake_message, mocker):
#     state = AsyncMock()
#     fake_message.text = "150"
#     fake_message.answer = AsyncMock()
#
#     # Мокаем confirm_arrival_keyboard
#     confirm_keyboard = MagicMock()
#     mocker.patch("bot.handlers.arrival.confirm_arrival_keyboard", return_value=confirm_keyboard)
#
#     await set_arrival_amount(fake_message, state)
#
#     state.update_data.assert_awaited_once_with(amount=150)
#     fake_message.answer.assert_awaited_once_with(
#         "Подтвердите приход: 150 кг", reply_markup=confirm_keyboard
#     )
#     state.set_state.assert_awaited_once_with(ArrivalState.confirm)
#
#
#
# @pytest.mark.asyncio
# async def test_confirm_arrival_handler_success(fake_callback, mocker):
#     state = AsyncMock()
#     session = AsyncMock()
#
#     # Подготовка данных
#     state.get_data.return_value = {"type": "pellets", "amount": 100}
#     fake_callback.from_user.id = 123
#     fake_callback.from_user.full_name = "Test User"
#
#     # Мокаем get_or_create_user и save_arrival
#     user_mock = MagicMock()
#     user_mock.id = 1
#     user_mock.role = "manager"
#     mocker.patch("bot.handlers.arrival.get_or_create_user", return_value=user_mock)
#     mock_save = mocker.patch("bot.handlers.arrival.save_arrival", new_callable=AsyncMock)
#
#     await confirm_arrival(fake_callback, state=state, session=session)
#
#     state.clear.assert_awaited_once()
#     fake_callback.message.edit_text.assert_awaited_once_with("✅ Приход успешно добавлен!")
#     mock_save.assert_awaited_once_with(session, type="pellets", amount=100, user_id=1)
#
#
#
# @pytest.mark.asyncio
# async def test_cancel_arrival_handler(fake_callback):
#     state = AsyncMock()
#
#     await cancel_arrival(fake_callback, state)
#
#     fake_callback.message.edit_text.assert_awaited_once_with("❌ Операция отменена.")
#     state.clear.assert_awaited_once()
