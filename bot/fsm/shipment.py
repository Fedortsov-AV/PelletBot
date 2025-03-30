from aiogram.fsm.state import State, StatesGroup

class ShipmentState(StatesGroup):
    waiting_for_small_packs = State()  # Ожидаем количество пачек 3 кг
    waiting_for_large_packs = State()  # Ожидаем количество пачек 5 кг