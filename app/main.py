import csv
import os

import cv2
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.db.base import SessionLocal
from app.models.inventory import Spool
from app.models.printer import Printer

app = FastAPI(
    title=settings.project_name, openapi_url=f"{settings.api_v1_str}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/")
def read_root():
    return {"message": "3D Ocean AI Monitoring System", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.on_event("startup")
def seed_data_on_startup():
    """Seed printers and spools from CSV if they don't already exist.
    CSV locations (mounted by docker-compose):
    - /app/data/seed/printers.csv
    - /app/data/seed/spools.csv
    """
    data_dir = os.environ.get("DATA_DIR", settings.data_dir)
    seed_dir = os.path.join(data_dir, "seed")
    printers_csv = os.path.join(seed_dir, "printers.csv")
    spools_csv = os.path.join(seed_dir, "spools.csv")
    # Ensure sample images directory has a few images for demo
    sample_dir = os.path.join(data_dir, "sample_images")
    os.makedirs(sample_dir, exist_ok=True)
    try:
        existing = [
            f
            for f in os.listdir(sample_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
        if len(existing) < 2:
            # Create one success and one failure image
            success = np.zeros((400, 600, 3), dtype=np.uint8)
            cv2.rectangle(success, (200, 150), (400, 350), (100, 100, 100), -1)
            cv2.imwrite(os.path.join(sample_dir, "success_demo.jpg"), success)

            failure = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
            cv2.line(failure, (100, 100), (500, 200), (255, 255, 255), 2)
            cv2.line(failure, (200, 300), (400, 100), (255, 255, 255), 2)
            cv2.imwrite(os.path.join(sample_dir, "failure_demo.jpg"), failure)
    except Exception:
        # Non-fatal; continue startup
        pass

    db = SessionLocal()
    try:
        # Seed printers
        if os.path.exists(printers_csv):
            with open(printers_csv, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    serial_no = row.get("serial_no")
                    if not serial_no:
                        continue
                    existing = (
                        db.query(Printer).filter(Printer.serial_no == serial_no).first()
                    )
                    if existing:
                        continue
                    printer = Printer(
                        serial_no=serial_no,
                        machine_name=row.get("machine_name") or serial_no,
                        location=row.get("location"),
                        model=row.get("model"),
                        max_bed_temp=float(row.get("max_bed_temp") or 0),
                        max_nozzle_temp=float(row.get("max_nozzle_temp") or 0),
                        status=row.get("status") or "idle",
                    )
                    db.add(printer)
            db.commit()

        # Seed spools
        if os.path.exists(spools_csv):
            with open(spools_csv, newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    spool_id = row.get("spool_id")
                    if not spool_id:
                        continue
                    existing = (
                        db.query(Spool).filter(Spool.spool_id == spool_id).first()
                    )
                    if existing:
                        continue
                    total = float(row.get("total_weight_g") or 0)
                    spool = Spool(
                        spool_id=spool_id,
                        material_type=row.get("material_type") or "PLA",
                        color=row.get("color"),
                        brand=row.get("brand"),
                        total_weight_g=total,
                        remaining_weight_g=total,
                        usage_percentage=0.0,
                        is_active=True,
                    )
                    db.add(spool)
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
