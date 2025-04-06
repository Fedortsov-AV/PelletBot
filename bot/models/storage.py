from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from bot.models.base import Base


class ProductStorage(Base):
    __tablename__ = "product_storage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    amount = Column(Integer, default=0)

    product = relationship("Product", back_populates="storage")


class RawMaterialStorage(Base):
    __tablename__ = "raw_material_storage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_product_id = Column(Integer, ForeignKey("raw_products.id", ondelete="CASCADE"), unique=True, nullable=False)
    amount = Column(Integer, default=0)

    raw_product = relationship("RawProduct", back_populates="storage")
