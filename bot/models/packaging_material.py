from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship
from bot.models.base import Base

class PackagingMaterial(Base):
    __tablename__ = "packaging_materials"
    id = Column(Integer, primary_key=True, autoincrement=True)
    packaging_id = Column(Integer, ForeignKey("packaging.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    cost = Column(Float, nullable=False)

    packaging = relationship("Packaging", back_populates="packaging_materials")
    material = relationship("Material")