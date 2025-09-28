from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    printer_id = Column(Integer, ForeignKey("printers.id"), nullable=False)

    # Job details
    part_name = Column(String, nullable=False)
    part_description = Column(Text)
    batch = Column(String)
    operator = Column(String)

    # Status and timing
    status = Column(
        String, default="queued"
    )  # queued, printing, completed, failed, cancelled
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    estimated_time_min = Column(Integer)
    actual_time_min = Column(Integer)

    # Material usage
    material_g = Column(Float)
    spool_id = Column(String)

    # Progress tracking
    progress_percentage = Column(Float, default=0.0)
    current_layer = Column(Integer, default=0)
    total_layers = Column(Integer)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    printer = relationship("Printer", back_populates="jobs")
    failure_events = relationship("FailureEvent", back_populates="job")


class FailureEvent(Base):
    __tablename__ = "failure_events"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("print_jobs.id"), nullable=False)
    failure_type = Column(
        String, nullable=False
    )  # layer_adhesion, warping, stringing, etc.
    confidence_score = Column(Float, nullable=False)
    image_path = Column(String)
    description = Column(Text)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved = Column(Boolean, default=False)

    # Relationships
    job = relationship("PrintJob", back_populates="failure_events")
