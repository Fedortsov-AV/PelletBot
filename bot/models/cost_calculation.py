from sqlalchemy import Column, Integer, Float, Date, DateTime
from sqlalchemy.sql import func
from bot.models.base import Base

class CostCalculation(Base):
    __tablename__ = "cost_calculations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    total_material_cost = Column(Float)
    total_overhead_cost = Column(Float)
    total_produced_kg = Column(Float)
    cost_per_kg = Column(Float)
    calculated_at = Column(DateTime, default=func.now())