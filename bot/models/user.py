from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from bot.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="anonymous")  # Роли: adminka, manager, user, anonymous
    arrivals = relationship("Arrival", back_populates="user")
    expenses = relationship("Expense", back_populates="user")
    packagings = relationship("Packaging", back_populates="user")
    shipments = relationship("Shipment", back_populates="user")  # Добавлена связь с отгрузками
