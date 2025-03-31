from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from bot.models.base import Base


class Storage(Base):
    __tablename__ = "storage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String, ForeignKey("products.name"), unique=True)
    amount = Column(Integer, default=0)


    product = relationship("Product", back_populates="storage")