from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, validates

from bot.models.base import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    weight = Column(Integer, nullable=False)
    raw_product_id = Column(Integer, ForeignKey("raw_products.id"), nullable=False)

    raw_material = relationship("RawProduct", back_populates="products")
    packagings = relationship("Packaging", back_populates="product")
    storage = relationship(
        "ProductStorage",
        back_populates="product",
        cascade="all, delete-orphan",
        single_parent=True
    )
    shipment_items = relationship("ShipmentItem", back_populates="product")

    @validates('weight')
    def validate_weight(self, key, weight):
        if weight <= 0:
            raise ValueError("Вес продукта должен быть положительным")
        return weight
