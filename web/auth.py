import os
import bcrypt
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Environment, FileSystemLoader
import jwt
from datetime import datetime, timedelta

from bot.config import SECRET_KEY, ALGORITHM
from bot.models.database import async_session
from bot.models.user import User
from .dependencies import get_db

router = APIRouter()

# Настройка Jinja2 окружения
env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")),
    auto_reload=True
)

ACCESS_TOKEN_EXPIRE_MINUTES = 60

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def authenticate_user(session: AsyncSession, username: str, password: str):
    from sqlalchemy import select
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return None
    return user

@router.get("/login")
async def login_page(request: Request):
    template = env.get_template("login.html")
    html = template.render({"request": request})
    return HTMLResponse(html)

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, username, password)
    if not user:
        template = env.get_template("login.html")
        html = template.render({"request": request, "error": "Неверный логин или пароль"})
        return HTMLResponse(html)
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response