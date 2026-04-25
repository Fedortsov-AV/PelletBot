import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from .auth import router as auth_router
from .dashboard import router as dashboard_router
from .arrivals import router as arrivals_router
from .packaging import router as packaging_router

app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(arrivals_router)
app.include_router(packaging_router)

@app.get("/")
async def root():
    return RedirectResponse(url="/login")


@app.on_event("startup")
async def startup():
    # Инициализация БД, если нужно
    from bot.models.database import init_db
    await init_db()