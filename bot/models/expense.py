from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from bot.models.base import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Integer, nullable=False)  # Сумма расхода
    purpose = Column(String, nullable=False)  # Назначение расхода
    source = Column(String, nullable=False)  # Источник: "собственные средства" или "касса"
    date = Column(DateTime, default=datetime.utcnow)  # Дата расхода
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ID пользователя

    user = relationship("User", back_populates="expenses")
