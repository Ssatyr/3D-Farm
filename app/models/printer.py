from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Printer(Base):
    __tablename__ = "printers"

    id = Column(Integer, primary_key=True, index=True)
    serial_no = Column(String, unique=True, index=True, nullable=False)
    machine_name = Column(String, nullable=False)
    status = Column(String, default="idle")  # idle, printing, error, maintenance
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Location and specs
    location = Column(String)
    model = Column(String)
    max_bed_temp = Column(Float)
    max_nozzle_temp = Column(Float)

    # Relationships
    jobs = relationship("PrintJob", back_populates="printer")
