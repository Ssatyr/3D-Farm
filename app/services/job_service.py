import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.inventory import Spool
from app.models.job import FailureEvent, PrintJob
from app.models.printer import Printer
from app.services.failure_detection import FailureDetector
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class JobService:
    def __init__(self, db: Session):
        self.db = db
        self.inventory_service = InventoryService(db)
        self.failure_detector = FailureDetector()
        self.last_error_message: Optional[str] = None

    def _set_error(self, message: str) -> None:
        self.last_error_message = message
        logger.error(message)

    def create_job(
        self,
        printer_id: int,
        part_name: str,
        part_description: str = None,
        batch: str = None,
        operator: str = None,
        estimated_time_min: int = None,
        material_g: float = None,
        spool_id: str = None,
        total_layers: int = None,
    ) -> Optional[PrintJob]:
        """Create a new print job"""
        try:
            # Validate entities exist (queuing allowed even if currently in use)
            printer = self.db.query(Printer).filter(Printer.id == printer_id).first()
            if not printer:
                self._set_error(f"Printer {printer_id} not found")
                return None
            # Only allow creation when printer is available (idle and active)
            if (printer.status != "idle") or (
                hasattr(printer, "is_active") and not printer.is_active
            ):
                self._set_error(
                    f"Printer {printer_id} is not available (status: {printer.status})"
                )
                return None
            if spool_id:
                spool = self._get_spool(spool_id)
                if not spool:
                    self._set_error(f"Spool {spool_id} not found")
                    return None

            job_id = f"JOB_{uuid.uuid4().hex[:8].upper()}"

            job = PrintJob(
                job_id=job_id,
                printer_id=printer_id,
                part_name=part_name,
                part_description=part_description,
                batch=batch,
                operator=operator,
                estimated_time_min=estimated_time_min,
                material_g=material_g,
                spool_id=spool_id,
                total_layers=total_layers,
                status="queued",
            )

            self.db.add(job)
            self.db.commit()
            logger.info(f"Created job {job_id} for printer {printer_id}")
            return job

        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            self.db.rollback()
            return None

    def start_job(self, job_id: str) -> bool:
        """Start a print job"""
        try:
            job = self._get_job(job_id)
            if not job:
                self._set_error(f"Job {job_id} not found")
                return False

            if job.status != "queued":
                self._set_error(f"Job {job_id} is not in queued status")
                return False

            # Validate printer still available
            printer = (
                self.db.query(Printer).filter(Printer.id == job.printer_id).first()
            )
            if not printer:
                self._set_error(f"Printer {job.printer_id} not found")
                return False
            if printer.status == "printing":
                self._set_error(f"Printer {job.printer_id} is occupied")
                return False

            # Validate spool still available
            if job.spool_id:
                spool = (
                    self.db.query(Spool)
                    .filter(Spool.spool_id == job.spool_id, Spool.is_active == True)
                    .first()
                )
                if not spool:
                    self._set_error(
                        f"Spool {job.spool_id} not found or inactive for job {job_id}"
                    )
                    return False
                if (
                    job.material_g is not None
                    and spool.remaining_weight_g < job.material_g
                ):
                    # Create an alert and persist it before failing start
                    try:
                        self.inventory_service.ensure_alert(
                            spool_id=job.spool_id,
                            alert_type="insufficient_material",
                            message=(
                                f"Spool {job.spool_id} has {spool.remaining_weight_g:.1f}g, "
                                f"job requires {job.material_g:.1f}g"
                            ),
                        )
                        self.db.commit()
                    except Exception as alert_ex:
                        logger.error(
                            f"Failed to create insufficient material alert on start: {str(alert_ex)}"
                        )
                        self.db.rollback()
                    self._set_error(
                        f"Spool {job.spool_id} has insufficient material for job {job_id}"
                    )
                    return False
                in_use = (
                    self.db.query(PrintJob)
                    .filter(
                        PrintJob.spool_id == job.spool_id, PrintJob.status == "printing"
                    )
                    .first()
                )
                if in_use:
                    self._set_error(
                        f"Spool {job.spool_id} already in use by job {in_use.job_id}"
                    )
                    return False

            # Update job status
            job.status = "printing"
            job.start_time = datetime.now(timezone.utc)

            # Update printer status
            if printer:
                printer.status = "printing"

            # Pre-calc insufficient material alert for this job
            try:
                if job.spool_id and job.material_g:
                    spool = self._get_spool(job.spool_id)
                    if spool and spool.remaining_weight_g < job.material_g:
                        self.inventory_service.ensure_alert(
                            spool_id=job.spool_id,
                            alert_type="insufficient_material",
                            message=(
                                f"Spool {job.spool_id} has {spool.remaining_weight_g:.1f}g, "
                                f"job requires {job.material_g:.1f}g"
                            ),
                        )
            except Exception as e:
                logger.error(f"Failed to create insufficient material alert: {str(e)}")

            self.db.commit()
            logger.info(f"Started job {job_id}")
            return True

        except Exception as e:
            self._set_error(f"Error starting job: {str(e)}")
            self.db.rollback()
            return False

    def update_job_progress(
        self, job_id: str, progress_percentage: float, current_layer: int = None
    ) -> bool:
        """Update job progress"""
        try:
            job = self._get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            # Calculate incremental material usage based on progress delta
            previous_progress = job.progress_percentage or 0.0
            new_progress = max(0.0, min(100.0, progress_percentage))
            delta = new_progress - previous_progress
            if delta > 0 and job.spool_id and job.material_g:
                material_used_delta = job.material_g * (delta / 100.0)
                try:
                    self.inventory_service.update_spool_usage(
                        job.spool_id, material_used_delta
                    )
                    # Re-check insufficient material condition for remaining portion
                    spool = self._get_spool(job.spool_id)
                    if spool and job.material_g:
                        remaining_needed = max(
                            0.0, job.material_g * (1 - new_progress / 100.0)
                        )
                        if spool.remaining_weight_g < remaining_needed:
                            self.inventory_service.ensure_alert(
                                spool_id=job.spool_id,
                                alert_type="insufficient_material",
                                message=(
                                    f"Spool {job.spool_id} may not complete job: "
                                    f"{spool.remaining_weight_g:.1f}g left, needs {remaining_needed:.1f}g"
                                ),
                            )
                except Exception as inv_err:
                    logger.error(
                        f"Failed updating spool usage on progress for job {job_id}: {str(inv_err)}"
                    )

            job.progress_percentage = new_progress
            if current_layer is not None:
                job.current_layer = current_layer

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error updating job progress: {str(e)}")
            self.db.rollback()
            return False

    def complete_job(self, job_id: str, success: bool = True) -> bool:
        """Complete a print job"""
        try:
            job = self._get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            # Update job status
            job.status = "completed" if success else "failed"
            job.end_time = datetime.now(timezone.utc)

            # Calculate actual time
            if job.start_time:
                duration = job.end_time - job.start_time
                job.actual_time_min = int(duration.total_seconds() / 60)

            # Update printer status
            printer = (
                self.db.query(Printer).filter(Printer.id == job.printer_id).first()
            )
            if printer:
                printer.status = "idle"

            # Update inventory if material was used (only for success, deduct remainder)
            if success and job.spool_id and job.material_g:
                used_so_far = (job.progress_percentage or 0.0) / 100.0 * job.material_g
                remaining = max(0.0, job.material_g - used_so_far)
                if remaining > 0:
                    self.inventory_service.update_spool_usage(job.spool_id, remaining)

            self.db.commit()
            logger.info(f"Completed job {job_id} with status: {job.status}")
            return True

        except Exception as e:
            logger.error(f"Error completing job: {str(e)}")
            self.db.rollback()
            return False

    def detect_failure_from_image(
        self, job_id: str, image_path: str
    ) -> Optional[FailureEvent]:
        """Detect failure from camera image"""
        try:
            job = self._get_job(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return None

            # Use AI detection
            is_failure, confidence, failure_type = self.failure_detector.detect_failure(
                image_path, job_id
            )

            if is_failure:
                # Update proportional material usage for up to the last 30 seconds
                try:
                    if job.spool_id and job.material_g:
                        total_minutes = job.estimated_time_min or 60
                        seconds_total = max(total_minutes * 60, 1)
                        elapsed_s = (
                            int(
                                (
                                    datetime.now(timezone.utc) - job.start_time
                                ).total_seconds()
                            )
                            if job.start_time
                            else 30
                        )
                        window_s = min(30, max(elapsed_s, 0))
                        used_g = (job.material_g * window_s) / seconds_total
                        if used_g > 0:
                            self.inventory_service.update_spool_usage(
                                job.spool_id, used_g
                            )
                except Exception as inv_ex:
                    logger.error(
                        f"Error updating spool usage on failure: {str(inv_ex)}"
                    )

                # Create failure event
                failure_event = FailureEvent(
                    job_id=job.id,
                    failure_type=failure_type,
                    confidence_score=confidence,
                    image_path=image_path,
                    description=f"AI detected {failure_type} with {confidence:.2f} confidence",
                )

                self.db.add(failure_event)

                # Update job status to failed
                job.status = "failed"
                job.end_time = datetime.now(timezone.utc)

                # Update printer status
                printer = (
                    self.db.query(Printer).filter(Printer.id == job.printer_id).first()
                )
                if printer:
                    printer.status = "error"
                # Lock spool until manually reactivated
                if job.spool_id:
                    spool = self._get_spool(job.spool_id)
                    if spool:
                        spool.is_active = False

                self.db.commit()
                logger.warning(f"Failure detected for job {job_id}: {failure_type}")
                return failure_event

            return None

        except Exception as e:
            logger.error(f"Error detecting failure: {str(e)}")
            self.db.rollback()
            return None

    def get_job_by_id(self, job_id: str) -> Optional[PrintJob]:
        """Get job by ID"""
        return self.db.query(PrintJob).filter(PrintJob.job_id == job_id).first()

    def get_active_jobs(self) -> List[PrintJob]:
        """Get all active jobs"""
        return (
            self.db.query(PrintJob)
            .filter(PrintJob.status.in_(["queued", "printing"]))
            .all()
        )

    def get_jobs_by_printer(self, printer_id: int) -> List[PrintJob]:
        """Get jobs for a specific printer"""
        return self.db.query(PrintJob).filter(PrintJob.printer_id == printer_id).all()

    def get_failure_events(self, job_id: str = None) -> List[FailureEvent]:
        """Get failure events, optionally filtered by job"""
        query = self.db.query(FailureEvent)
        if job_id:
            job = self.db.query(PrintJob).filter(PrintJob.job_id == job_id).first()
            if job:
                query = query.filter(FailureEvent.job_id == job.id)
        return query.all()

    def delete_job(self, job_id: str) -> bool:
        """Delete a job only if it's still queued."""
        try:
            job = self.db.query(PrintJob).filter(PrintJob.job_id == job_id).first()
            if not job:
                self._set_error(f"Job {job_id} not found")
                return False
            if job.status != "queued":
                self._set_error("Only queued jobs can be deleted")
                return False
            self.db.delete(job)
            self.db.commit()
            logger.info(f"Deleted queued job {job_id}")
            return True
        except Exception as e:
            self._set_error(f"Error deleting job: {str(e)}")
            self.db.rollback()
            return False

    # Internal helpers
    def _get_job(self, job_id: str) -> Optional[PrintJob]:
        return self.db.query(PrintJob).filter(PrintJob.job_id == job_id).first()

    def _get_spool(self, spool_id: str) -> Optional[Spool]:
        return self.db.query(Spool).filter(Spool.spool_id == spool_id).first()
