from aiogram import Dispatcher
# from bot.handlers import start  # Импортируем все обработчики

def register_handlers(dp: Dispatcher):
    from bot.handlers import start, admin, info, arrival, expense, packaging, statistics, shipment
    from bot.handlers.adminka import add_handlers, edit_handlers, cancel_handlers
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(info.router)
    dp.include_router(arrival.router)
    dp.include_router(expense.router)
    dp.include_router(packaging.router)
    dp.include_router(statistics.router)
    dp.include_router(shipment.router)
    dp.include_router(add_handlers.router)
    dp.include_router(edit_handlers.router)
    dp.include_router(cancel_handlers.router)