import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.inventory import InventoryAlert, Spool
from app.models.job import PrintJob

logger = logging.getLogger(__name__)


class InventoryService:
    def __init__(self, db: Session):
        self.db = db
        self.alert_threshold = settings.inventory_alert_threshold

    def update_spool_usage(self, spool_id: str, material_used_g: float) -> bool:
        """Update spool usage and check for alerts"""
        try:
            spool = self.db.query(Spool).filter(Spool.spool_id == spool_id).first()
            if not spool:
                logger.error(f"Spool {spool_id} not found")
                return False

            # Update remaining weight
            spool.remaining_weight_g -= material_used_g
            spool.remaining_weight_g = max(
                0, spool.remaining_weight_g
            )  # Don't go below 0

            # Calculate usage percentage
            spool.usage_percentage = (
                spool.total_weight_g - spool.remaining_weight_g
            ) / spool.total_weight_g

            # Check for low inventory
            remaining_percentage = spool.remaining_weight_g / spool.total_weight_g
            was_low = spool.is_low_inventory
            spool.is_low_inventory = remaining_percentage <= self.alert_threshold

            # Create alert if inventory is low and wasn't before
            if spool.is_low_inventory and not was_low:
                self._create_inventory_alert(spool, remaining_percentage)

            # If any active job uses this spool, ensure 'insufficient_material' alert
            # when the remaining material cannot cover the job's remaining requirement.
            active_jobs = (
                self.db.query(PrintJob)
                .filter(
                    PrintJob.spool_id == spool.spool_id, PrintJob.status == "printing"
                )
                .all()
            )
            for job in active_jobs:
                if job.material_g is None:
                    continue
                progress = job.progress_percentage or 0.0
                remaining_needed = max(0.0, job.material_g * (1.0 - progress / 100.0))
                if spool.remaining_weight_g < remaining_needed:
                    try:
                        self.ensure_alert(
                            spool_id=spool.spool_id,
                            alert_type="insufficient_material",
                            message=(
                                f"Spool {spool.spool_id} may not complete job: "
                                f"{spool.remaining_weight_g:.1f}g left, needs {remaining_needed:.1f}g"
                            ),
                        )
                    except Exception as ensure_ex:
                        logger.error(
                            f"Failed to ensure insufficient material alert: {str(ensure_ex)}"
                        )

            self.db.commit()
            logger.info(
                f"Updated spool {spool_id}: {spool.remaining_weight_g:.1f}g remaining ({remaining_percentage:.1%})"
            )
            return True

        except Exception as e:
            logger.error(f"Error updating spool usage: {str(e)}")
            self.db.rollback()
            return False

    def _create_inventory_alert(self, spool: Spool, remaining_percentage: float):
        """Create an inventory alert"""
        alert = InventoryAlert(
            spool_id=spool.spool_id,
            alert_type="low_inventory",
            threshold_percentage=self.alert_threshold,
            current_percentage=remaining_percentage,
            message=f"Spool {spool.spool_id} ({spool.material_type}) is running low: {remaining_percentage:.1%} remaining",
        )
        self.db.add(alert)
        logger.warning(f"Created inventory alert for spool {spool.spool_id}")

    def get_low_inventory_spools(self) -> List[Spool]:
        """Get all spools with low inventory"""
        return self.db.query(Spool).filter(Spool.is_low_inventory == True).all()

    def get_active_alerts(self) -> List[InventoryAlert]:
        """Get all unresolved inventory alerts"""
        return (
            self.db.query(InventoryAlert)
            .filter(InventoryAlert.is_resolved == False)
            .all()
        )

    def resolve_alert(self, alert_id: int) -> bool:
        """Mark an alert as resolved"""
        try:
            alert = (
                self.db.query(InventoryAlert)
                .filter(InventoryAlert.id == alert_id)
                .first()
            )
            if alert:
                alert.is_resolved = True
                self.db.commit()
                logger.info(f"Resolved alert {alert_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error resolving alert: {str(e)}")
            self.db.rollback()
            return False

    def create_spool(
        self,
        spool_id: str,
        material_type: str,
        total_weight_g: float,
        color: str = None,
        brand: str = None,
    ) -> bool:
        """Create a new spool"""
        try:
            spool = Spool(
                spool_id=spool_id,
                material_type=material_type,
                color=color,
                brand=brand,
                total_weight_g=total_weight_g,
                remaining_weight_g=total_weight_g,
                usage_percentage=0.0,
            )
            self.db.add(spool)
            self.db.commit()
            logger.info(f"Created new spool: {spool_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating spool: {str(e)}")
            self.db.rollback()
            return False

    def get_spool_by_id(self, spool_id: str) -> Optional[Spool]:
        """Get spool by ID"""
        return self.db.query(Spool).filter(Spool.spool_id == spool_id).first()

    def get_all_spools(self) -> List[Spool]:
        """Get all active spools"""
        return self.db.query(Spool).filter(Spool.is_active == True).all()

    def get_all_spools_including_inactive(self) -> List[Spool]:
        """Get all spools (active and inactive)."""
        return self.db.query(Spool).all()

    def ensure_alert(
        self,
        spool_id: str,
        alert_type: str,
        message: str,
        threshold_percentage: float | None = None,
        current_percentage: float | None = None,
    ) -> None:
        """Create an alert if an unresolved alert of the same type doesn't already exist for this spool."""
        existing = (
            self.db.query(InventoryAlert)
            .filter(
                InventoryAlert.spool_id == spool_id,
                InventoryAlert.alert_type == alert_type,
                InventoryAlert.is_resolved == False,
            )
            .first()
        )
        if existing:
            return
        alert = InventoryAlert(
            spool_id=spool_id,
            alert_type=alert_type,
            threshold_percentage=threshold_percentage or 0.0,
            current_percentage=current_percentage or 0.0,
            message=message,
        )
        self.db.add(alert)
