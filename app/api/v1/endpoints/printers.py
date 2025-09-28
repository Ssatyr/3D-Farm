from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.printer import Printer
from app.schemas.printer_schemas import (
    PrinterCreate,
    PrinterResponse,
    PrinterStatusUpdate,
)

router = APIRouter()


@router.post("/", response_model=PrinterResponse)
def create_printer(printer_data: PrinterCreate, db: Session = Depends(get_db)):
    """Create a new printer"""
    # Check if serial number already exists
    existing = (
        db.query(Printer).filter(Printer.serial_no == printer_data.serial_no).first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Printer with this serial number already exists"
        )

    printer = Printer(
        serial_no=printer_data.serial_no,
        machine_name=printer_data.machine_name,
        location=printer_data.location,
        model=printer_data.model,
        max_bed_temp=printer_data.max_bed_temp,
        max_nozzle_temp=printer_data.max_nozzle_temp,
    )

    db.add(printer)
    db.commit()
    db.refresh(printer)

    return printer


@router.get("/", response_model=List[PrinterResponse])
def get_printers(db: Session = Depends(get_db)):
    """Get all printers"""
    return db.query(Printer).filter(Printer.is_active == True).all()


@router.get("/{printer_id}", response_model=PrinterResponse)
def get_printer(printer_id: int, db: Session = Depends(get_db)):
    """Get a specific printer"""
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    return printer


@router.put("/{printer_id}/status")
def update_printer_status(
    printer_id: int, status_data: PrinterStatusUpdate, db: Session = Depends(get_db)
):
    """Update printer status"""
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    printer.status = status_data.status
    db.commit()

    return {"message": f"Printer {printer_id} status updated to {status_data.status}"}


@router.post("/{printer_id}/activate")
def activate_printer(printer_id: int, db: Session = Depends(get_db)):
    """Set printer status to idle (reactivate)."""
    printer = db.query(Printer).filter(Printer.id == printer_id).first()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    printer.status = "idle"
    db.commit()
    return {"message": f"Printer {printer_id} set to idle"}
