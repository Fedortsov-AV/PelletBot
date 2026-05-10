from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from bot.models.base import Base

class MaterialMovement(Base):
    __tablename__ = "material_movements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    type = Column(String, nullable=False)  # 'in' или 'out'
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    unit_price = Column(Float)  # цена за единицу при приходе
    remaining_quantity = Column(Float)  # остаток для списания (только для приходов)
    date = Column(DateTime, default=func.now())
    expense_id = Column(Integer, ForeignKey("expenses.id"))
    packaging_id = Column(Integer, ForeignKey("packaging.id"))

    material = relationship("Material")
    expense = relationship("Expense", foreign_keys=[expense_id])
    packaging = relationship("Packaging", foreign_keys=[packaging_id])