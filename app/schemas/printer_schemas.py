from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PrinterCreate(BaseModel):
    serial_no: str
    machine_name: str
    location: Optional[str] = None
    model: Optional[str] = None
    max_bed_temp: Optional[float] = None
    max_nozzle_temp: Optional[float] = None


class PrinterResponse(BaseModel):
    id: int
    serial_no: str
    machine_name: str
    status: str
    is_active: bool
    location: Optional[str]
    model: Optional[str]
    max_bed_temp: Optional[float]
    max_nozzle_temp: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PrinterStatusUpdate(BaseModel):
    status: str
