from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from bot.models.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    weight = Column(Integer, nullable=False)
    raw_product_id = Column(Integer, ForeignKey("raw_products.id"), nullable=True)

    raw_material = relationship("RawProduct", back_populates="products")
    packagings = relationship("Packaging", back_populates="product")
    storage = relationship("ProductStorage", back_populates="product")
    shipment_items = relationship("ShipmentItem", back_populates="product")