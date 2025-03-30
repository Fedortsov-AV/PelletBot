from aiogram.fsm.state import State, StatesGroup

class PackagingStates(StatesGroup):
    waiting_for_small_packs = State()
    waiting_for_large_packs = State()
    waiting_for_ratio = State()
