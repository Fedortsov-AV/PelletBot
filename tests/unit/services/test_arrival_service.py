import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from sqlalchemy import select, extract, BinaryExpression
from sqlalchemy.exc import SQLAlchemyError

from bot.models.arrival import Arrival
from bot.models.rawProduct import RawProduct
from bot.services.arrival import (
    add_arrival,
    get_arrival_by_id,
    get_arrivals_for_month,
    delete_arrival,
    update_arrival_amount,
    get_raw_product_names
)


@pytest.mark.asyncio
async def test_add_arrival_success(mock_db_session):
    # Мокируем зависимости
    mock_user = MagicMock()
    mock_user.id = 1
    mock_db_session.execute.return_value = MagicMock(scalars=MagicMock(first=MagicMock(return_value=mock_user)))

    # Мокируем update_stock_arrival
    with patch('bot.services.arrival.update_stock_arrival', new=AsyncMock()) as mock_update:
        result = await add_arrival(mock_db_session, 123, "test_type", 10)

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_update.assert_called_once_with(mock_db_session, "test_type", 10)
    assert isinstance(result, Arrival)


@pytest.mark.asyncio
async def test_add_arrival_rollback(mock_db_session):
    with patch('bot.services.arrival.update_stock_arrival', side_effect=SQLAlchemyError()), \
            pytest.raises(SQLAlchemyError):
        await add_arrival(mock_db_session, 123, "test_type", 10)
        mock_db_session.rollback.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_get_arrival_by_id(mock_db_session):
    test_arrival = Arrival(id=1, amount=10)
    mock_db_session.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=test_arrival)
    )

    result = await get_arrival_by_id(mock_db_session, 1)
    assert result.id == 1
    assert result.amount == 10


@pytest.mark.asyncio
async def test_get_arrivals_for_month(mock_db_session):
    # Создаем мок-объекты для прихода
    mock_arrival_1 = MagicMock(spec=Arrival)
    mock_arrival_2 = MagicMock(spec=Arrival)

    # Мокаем результат выполнения запроса
    mock_db_session.execute.return_value.scalars.return_value.all.return_value = [mock_arrival_1, mock_arrival_2]

    # Вызываем функцию, которую тестируем
    result = await get_arrivals_for_month(mock_db_session, 1)

    # Проверяем, что функция вернула правильное количество элементов (два прихода)
    assert len(result) == 2

    # Дополнительные проверки (если необходимо)
    assert result[0] == mock_arrival_1
    assert result[1] == mock_arrival_2

    # Проверяем, что запрос был выполнен с фильтрацией по месяцу
    mock_db_session.execute.assert_called_once()
    args, kwargs = mock_db_session.execute.call_args
    # Получаем объект select, который был передан в execute
    query = args[0]

    # Мы проверяем, что фильтрация идет по месяцу и что используется текущий месяц
    current_month = datetime.utcnow().month

    # Проверяем, что запрос содержит фильтрацию с использованием extract по месяцу
    # Вместо использования _whereclause, мы сравниваем сам запрос
    expected_filter = extract('month', Arrival.date) == current_month
    actual_filter = query._whereclause
    assert str(expected_filter) in str(actual_filter)

# @pytest.mark.asyncio
# async def test_get_arrivals_for_month(mock_db_session):
#     mock_arrival = MagicMock()
#     mock_db_session.execute.return_value = MagicMock(
#         scalars=MagicMock(all=MagicMock(return_value=[mock_arrival]))
#     )
#     result = await get_arrivals_for_month(mock_db_session, 1)
#     assert len(result) >= 1

@pytest.mark.asyncio
async def test_delete_arrival_success(mock_db_session):
    # Создаем объект "прихода", который будем удалять
    test_arrival = Arrival(id=1)

    # Мокаем результат выполнения запроса select, чтобы вернуть test_arrival
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = test_arrival

    # Вызываем функцию для удаления
    result = await delete_arrival(mock_db_session, 1)

    # Проверяем, что метод delete был вызван с правильным объектом
    mock_db_session.delete.assert_called_once_with(test_arrival)

    # Проверяем, что метод commit был вызван
    mock_db_session.commit.assert_called_once()

    # Проверяем, что функция вернула правильный объект (удаленный приход)
    assert result == test_arrival


@pytest.mark.asyncio
async def test_update_arrival_amount_success(mock_db_session):
    # Создаем объект "прихода", который будем обновлять
    test_arrival = Arrival(id=1, amount=5, type="old_type")

    # Мокаем результат выполнения запроса select, чтобы вернуть test_arrival
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = test_arrival

    # Патчим update_stock_arrival, чтобы проверить, был ли он вызван
    with patch('bot.services.arrival.update_stock_arrival', new=AsyncMock()) as mock_update:
        # Вызываем функцию для обновления
        result = await update_arrival_amount(mock_db_session, 1, 10, "new_type")

    # Проверяем, что количество и тип прихода обновились
    assert result.amount == 10
    assert result.type == "new_type"

    # Проверяем, что update_stock_arrival был вызван с правильными аргументами
    # Дельта = новый amount - старый amount
    mock_update.assert_called_once_with(mock_db_session, "new_type", 5)

    # Проверяем, что commit был вызван один раз
    mock_db_session.commit.assert_called_once()

@ pytest.mark.asyncio
async def test_get_raw_product_names(mock_db_session):
                mock_db_session.execute.return_value = MagicMock(
                    all=MagicMock(return_value=[("product1",), ("product2",)])
                )

                result = await get_raw_product_names(mock_db_session)
                assert result == ["product1", "product2"]