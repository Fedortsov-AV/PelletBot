import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(",")))
print(f'ADMIN_IDS: {ADMIN_IDS}')
# DATABASE_URL = os.getenv("DATABASE_URL")
# DATABASE_URL = "sqlite+aiosqlite:///warehouse_bot.db"  # Асинхронное подключение

db_path = os.getenv("DATABASE_URL")

if db_path and db_path.startswith("sqlite+aiosqlite:///"):
    # Извлекаем путь из URL
    relative_path = db_path.replace("sqlite+aiosqlite:///", "")

    # Если путь относительный, делаем абсолютным относительно корня проекта
    if not os.path.isabs(relative_path):
        # Определяем корневую директорию проекта
        BASE_DIR = Path(__file__).resolve().parent.parent  # Поднимаемся на 2 уровня: config.py -> bot/ -> корень
        absolute_path = BASE_DIR / relative_path
        DATABASE_URL = f"sqlite+aiosqlite:///{absolute_path}"
    else:
        DATABASE_URL = db_path
else:
    DATABASE_URL = db_path

# Для отладки
print(f"Database path: {DATABASE_URL}")