from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from bot.models.base import Base

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Кто отгрузил
    timestamp = Column(DateTime, default=func.now())  # Время отгрузки

    user = relationship("User", back_populates="shipments")
    shipment_items = relationship("ShipmentItem", back_populates="shipment")  # Связь через промежуточную таблицу


class ShipmentItem(Base):
    """Промежуточная таблица для связи Отгрузок и Продуктов (многие-ко-многим)"""
    __tablename__ = "shipment_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)  # Количество единиц данного продукта в отгрузке

    shipment = relationship("Shipment", back_populates="shipment_items")
    product = relationship("Product", back_populates="shipment_items")
