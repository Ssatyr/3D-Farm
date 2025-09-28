from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_job_service
from app.core.config import settings
from app.schemas.job_schemas import (
    FailureDetectionRequest,
    FailureEventResponse,
    JobProgressUpdate,
    PrintJobCreate,
    PrintJobResponse,
)
from app.services.job_service import JobService
from app.utils.file_utils import save_upload_to_data

router = APIRouter()


@router.post("/", response_model=PrintJobResponse)
def create_job(
    job_data: PrintJobCreate, job_service: JobService = Depends(get_job_service)
):
    """Create a new print job"""
    job = job_service.create_job(
        printer_id=job_data.printer_id,
        part_name=job_data.part_name,
        part_description=job_data.part_description,
        batch=job_data.batch,
        operator=job_data.operator,
        estimated_time_min=job_data.estimated_time_min,
        material_g=job_data.material_g,
        spool_id=job_data.spool_id,
        total_layers=job_data.total_layers,
    )

    if not job:
        raise HTTPException(status_code=400, detail="Failed to create job")

    return job


@router.get("/", response_model=List[PrintJobResponse])
def get_active_jobs(job_service: JobService = Depends(get_job_service)):
    """Get all active jobs"""
    return job_service.get_active_jobs()


@router.get("/failure-events", response_model=List[FailureEventResponse])
def get_all_failure_events(job_service: JobService = Depends(get_job_service)):
    """Get all failure events across all jobs (non-conflicting static route)."""
    return job_service.get_failure_events()


@router.post("/{job_id}/start")
def start_job(job_id: str, job_service: JobService = Depends(get_job_service)):
    """Start a print job"""
    success = job_service.start_job(job_id)
    if not success:
        detail = job_service.last_error_message or "Failed to start job"
        raise HTTPException(status_code=400, detail=detail)
    return {"message": f"Job {job_id} started successfully"}


@router.post("/{job_id}/progress")
def update_job_progress(
    job_id: str,
    progress_data: JobProgressUpdate,
    job_service: JobService = Depends(get_job_service),
):
    """Update job progress"""
    success = job_service.update_job_progress(
        job_id, progress_data.progress_percentage, progress_data.current_layer
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update job progress")
    return {"message": f"Job {job_id} progress updated"}


@router.post("/{job_id}/complete")
def complete_job(
    job_id: str,
    success: bool = True,
    job_service: JobService = Depends(get_job_service),
):
    """Complete a print job"""
    success_result = job_service.complete_job(job_id, success)
    if not success_result:
        detail = job_service.last_error_message or "Failed to complete job"
        raise HTTPException(status_code=400, detail=detail)
    return {"message": f"Job {job_id} completed"}


@router.post("/{job_id}/failure-detection")
def detect_failure(
    job_id: str,
    file: UploadFile = File(...),
    job_service: JobService = Depends(get_job_service),
):
    """Detect failure from uploaded image"""
    return _handle_frame_detection(job_id, file, job_service)


@router.post("/{job_id}/verify")
def verify_frame(
    job_id: str,
    file: UploadFile = File(...),
    job_service: JobService = Depends(get_job_service),
):
    """Verify a single camera frame for failure (production-like endpoint)."""
    return _handle_frame_detection(job_id, file, job_service)


@router.get("/by-job/{job_id}/failures", response_model=List[FailureEventResponse])
def get_job_failures(job_id: str, job_service: JobService = Depends(get_job_service)):
    """Get failure events for a job"""
    return job_service.get_failure_events(job_id)


@router.get("/{job_id}", response_model=PrintJobResponse)
def get_job(job_id: str, job_service: JobService = Depends(get_job_service)):
    """Get a specific job"""
    job = job_service.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}")
def delete_job(job_id: str, job_service: JobService = Depends(get_job_service)):
    """Delete a queued job"""
    success = job_service.delete_job(job_id)
    if not success:
        detail = job_service.last_error_message or "Failed to delete job"
        raise HTTPException(status_code=400, detail=detail)
    return {"message": f"Job {job_id} deleted"}


def _handle_frame_detection(
    job_id: str, file: UploadFile, job_service: JobService
) -> Dict[str, Any]:
    """Shared handler to save the uploaded frame and trigger detection."""
    try:
        file_path = save_upload_to_data(
            file, settings.data_dir, job_id=job_id, subdir="frames"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed saving frame: {str(e)}")

    failure_event = job_service.detect_failure_from_image(job_id, file_path)

    if failure_event:
        return {
            "failure_detected": True,
            "failure_type": failure_event.failure_type,
            "confidence": failure_event.confidence_score,
            "message": failure_event.description,
        }
    return {"failure_detected": False, "message": "No failure detected"}
