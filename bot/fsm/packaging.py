from aiogram.fsm.state import State, StatesGroup


class PackagingStates(StatesGroup):
    waiting_for_raw_material = State()
    waiting_for_product = State()
    waiting_for_amount = State()
    waiting_for_ratio = State()
    waiting_for_done_raw_material = State()
