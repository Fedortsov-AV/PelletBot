from sqlalchemy import Column, Integer, String
from bot.models.base import Base

class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)