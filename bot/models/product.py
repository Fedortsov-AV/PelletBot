from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from bot.models.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    weight = Column(Integer, nullable=False)

    packagings = relationship("Packaging", back_populates="product")
    shipments = relationship("Shipment", back_populates="user")
