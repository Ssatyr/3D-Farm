from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_inventory_service
from app.schemas.inventory_schemas import (
    InventoryAlertResponse,
    SpoolCreate,
    SpoolResponse,
    SpoolUsageUpdate,
)
from app.services.inventory_service import InventoryService

router = APIRouter()


@router.post("/spools", response_model=SpoolResponse)
def create_spool(
    spool_data: SpoolCreate,
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Create a new spool"""
    success = inventory_service.create_spool(
        spool_id=spool_data.spool_id,
        material_type=spool_data.material_type,
        total_weight_g=spool_data.total_weight_g,
        color=spool_data.color,
        brand=spool_data.brand,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to create spool")

    spool = inventory_service.get_spool_by_id(spool_data.spool_id)
    return spool


@router.get("/spools", response_model=List[SpoolResponse])
def get_spools(inventory_service: InventoryService = Depends(get_inventory_service)):
    """Get all spools"""
    return inventory_service.get_all_spools()


@router.get("/spools/all", response_model=List[SpoolResponse])
def get_all_spools(
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Get all spools including inactive"""
    return inventory_service.get_all_spools_including_inactive()


@router.get("/spools/{spool_id}", response_model=SpoolResponse)
def get_spool(
    spool_id: str, inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Get a specific spool"""
    spool = inventory_service.get_spool_by_id(spool_id)
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")
    return spool


@router.post("/spools/usage")
def update_spool_usage(
    usage_data: SpoolUsageUpdate,
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Update spool usage"""
    success = inventory_service.update_spool_usage(
        usage_data.spool_id, usage_data.material_used_g
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update spool usage")
    return {"message": f"Updated usage for spool {usage_data.spool_id}"}


@router.get("/alerts", response_model=List[InventoryAlertResponse])
def get_alerts(inventory_service: InventoryService = Depends(get_inventory_service)):
    """Get all active inventory alerts"""
    return inventory_service.get_active_alerts()


@router.get("/alerts/low-inventory")
def get_low_inventory_spools(
    inventory_service: InventoryService = Depends(get_inventory_service),
):
    """Get spools with low inventory"""
    return inventory_service.get_low_inventory_spools()


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int, inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Resolve an inventory alert"""
    success = inventory_service.resolve_alert(alert_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resolve alert")
    return {"message": f"Alert {alert_id} resolved"}


@router.post("/spools/{spool_id}/activate")
def activate_spool(
    spool_id: str, inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Reactivate a spool (after resolving failure)."""
    spool = inventory_service.get_spool_by_id(spool_id)
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")
    spool.is_active = True
    inventory_service.db.commit()
    return {"message": f"Spool {spool_id} activated"}


@router.post("/spools/{spool_id}/deactivate")
def deactivate_spool(
    spool_id: str, inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Deactivate a spool (e.g., after a failure)."""
    spool = inventory_service.get_spool_by_id(spool_id)
    if not spool:
        raise HTTPException(status_code=404, detail="Spool not found")
    spool.is_active = False
    inventory_service.db.commit()
    return {"message": f"Spool {spool_id} deactivated"}
