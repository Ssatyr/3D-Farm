from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.db.base import Base


class Spool(Base):
    __tablename__ = "spools"

    id = Column(Integer, primary_key=True, index=True)
    spool_id = Column(String, unique=True, index=True, nullable=False)
    material_type = Column(String, nullable=False)  # PLA, ABS, PETG, etc.
    color = Column(String)
    brand = Column(String)

    # Capacity and usage
    total_weight_g = Column(Float, nullable=False)
    remaining_weight_g = Column(Float, nullable=False)
    usage_percentage = Column(Float, default=0.0)

    # Status
    is_active = Column(Boolean, default=True)
    is_low_inventory = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class InventoryAlert(Base):
    __tablename__ = "inventory_alerts"

    id = Column(Integer, primary_key=True, index=True)
    spool_id = Column(String, nullable=False)
    alert_type = Column(String, nullable=False)  # low_inventory, empty, etc.
    threshold_percentage = Column(Float, nullable=False)
    current_percentage = Column(Float, nullable=False)
    message = Column(String, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
