import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from bot.fsm.arrival import ArrivalState


@pytest.mark.asyncio
async def test_arrival_fsm_states():
    storage = MemoryStorage()
    state = FSMContext(storage, "test_user")

    # Проверяем начальное состояние
    assert await state.get_state() is None

    # Устанавливаем состояние выбора типа
    await state.set_state(ArrivalState.type)
    assert await state.get_state() == ArrivalState.type

    # Обновляем данные
    await state.update_data(type="test_type")
    data = await state.get_data()
    assert data["type"] == "test_type"

    # Переходим в состояние количества
    await state.set_state(ArrivalState.amount)
    assert await state.get_state() == ArrivalState.amount