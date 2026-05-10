from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship

from bot.models.base import Base
from bot.models.material import Material
from bot.models.packaging import Packaging

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amount = Column(Integer, nullable=False)  # Сумма расхода
    purpose = Column(String, nullable=False)  # Назначение расхода
    source = Column(String, nullable=False)  # Источник: "собственные средства" или "касса"
    date = Column(DateTime, default=datetime.utcnow)  # Дата расхода
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ID пользователя
    category = Column(
        String)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    packaging_id = Column(Integer, ForeignKey("packaging.id"), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="expenses")
    material = relationship("Material", foreign_keys=[material_id])
    employee = relationship("User", foreign_keys=[employee_id])
    packaging = relationship("Packaging", foreign_keys=[packaging_id])
