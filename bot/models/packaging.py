from datetime import datetime

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship

from bot.models.base import Base
from bot.models.packaging_material import PackagingMaterial

class Packaging(Base):
    __tablename__ = "packaging"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    amount = Column(Integer, nullable=False, server_default="0")
    used_raw_material = Column(Integer, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    raw_product_id = Column(Integer, ForeignKey("raw_products.id"), nullable=False)  # Связь с сырьем
    total_material_cost = Column(Float, default=0.0)

    user = relationship("User", back_populates="packagings")
    product = relationship("Product", back_populates="packagings")
    raw_product = relationship("RawProduct", back_populates="packagings")
    packaging_materials = relationship("PackagingMaterial", back_populates="packaging")