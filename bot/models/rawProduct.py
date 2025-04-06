from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from bot.models.base import Base


class RawProduct(Base):
    __tablename__ = "raw_products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)

    products = relationship(
        "Product",
        back_populates="raw_material"
    )
    storage = relationship(
        "RawMaterialStorage",
        back_populates="raw_product",
        cascade="all, delete-orphan",
        single_parent=True
    )
    packagings = relationship("Packaging", back_populates="raw_product")
