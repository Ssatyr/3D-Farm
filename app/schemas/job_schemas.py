from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PrintJobCreate(BaseModel):
    printer_id: int
    part_name: str
    part_description: Optional[str] = None
    batch: Optional[str] = None
    operator: Optional[str] = None
    estimated_time_min: Optional[int] = None
    material_g: Optional[float] = None
    spool_id: Optional[str] = None
    total_layers: Optional[int] = None


class PrintJobResponse(BaseModel):
    id: int
    job_id: str
    printer_id: int
    part_name: str
    part_description: Optional[str]
    batch: Optional[str]
    operator: Optional[str]
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    estimated_time_min: Optional[int]
    actual_time_min: Optional[int]
    material_g: Optional[float]
    spool_id: Optional[str]
    progress_percentage: float
    current_layer: Optional[int]
    total_layers: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class FailureEventResponse(BaseModel):
    id: int
    job_id: int
    failure_type: str
    confidence_score: float
    image_path: Optional[str]
    description: Optional[str]
    detected_at: datetime
    resolved: bool

    class Config:
        from_attributes = True


class JobProgressUpdate(BaseModel):
    progress_percentage: float
    current_layer: Optional[int] = None


class FailureDetectionRequest(BaseModel):
    job_id: str
    image_path: str
