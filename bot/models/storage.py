from sqlalchemy import Column, Integer
from bot.models.base import Base


class Storage(Base):
    __tablename__ = "storage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pellets_6mm = Column(Integer, default=0)  # Количество пеллет 6 мм (кг)
    packs_3kg = Column(Integer, default=0)  # Количество пачек по 3 кг
    packs_5kg = Column(Integer, default=0)  # Количество пачек по 5 кг
