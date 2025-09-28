from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SpoolCreate(BaseModel):
    spool_id: str
    material_type: str
    total_weight_g: float
    color: Optional[str] = None
    brand: Optional[str] = None


class SpoolResponse(BaseModel):
    id: int
    spool_id: str
    material_type: str
    color: Optional[str]
    brand: Optional[str]
    total_weight_g: float
    remaining_weight_g: float
    usage_percentage: float
    is_active: bool
    is_low_inventory: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class InventoryAlertResponse(BaseModel):
    id: int
    spool_id: str
    alert_type: str
    threshold_percentage: float
    current_percentage: float
    message: str
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


class SpoolUsageUpdate(BaseModel):
    spool_id: str
    material_used_g: float
