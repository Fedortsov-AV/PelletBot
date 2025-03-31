from sqlalchemy import Column, Integer, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime
from bot.models.base import Base

class Packaging(Base):
    __tablename__ = "packaging"

    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_name = Column(String, unique=True)
    weight = Column(Integer, nullable=False)
    used_raw_material = Column(Integer, nullable=False)  # Сколько первичной продукции ушло
    date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="packagings")
