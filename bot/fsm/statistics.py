from aiogram.fsm.state import State, StatesGroup

class StatisticsStates(StatesGroup):
    select_period_packed = State()
    select_period_arrivals = State()
