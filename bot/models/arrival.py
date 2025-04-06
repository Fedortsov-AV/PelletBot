from datetime import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from bot.models.base import Base


class Arrival(Base):
    __tablename__ = "arrivals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="arrivals")
