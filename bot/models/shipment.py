from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from bot.models.base import Base

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Ссылка на пользователя
    small_packs = Column(Integer, default=0)  # Количество пачек по 3 кг
    large_packs = Column(Integer, default=0)  # Количество пачек по 5 кг
    timestamp = Column(DateTime, default=func.now())  # Время отгрузки

    user = relationship("User", back_populates="shipments")
