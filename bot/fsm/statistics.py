from aiogram.fsm.state import State, StatesGroup

class StatisticsStates(StatesGroup):
    select_period_packed = State()
    select_period_arrivals = State()
    wait_packed_period = State()
    wait_arrivals_period = State()
    waiting_shipments_start_date = State()
    waiting_shipments_end_date = State()