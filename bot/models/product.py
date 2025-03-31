from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from bot.models.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    weight = Column(Integer, nullable=False)
    is_raw = Column(Boolean, default=False)

    packagings = relationship("Packaging", back_populates="products")
    shipments = relationship("Shipment", back_populates="products")
    storage = relationship("Storage", back_populates="products")
