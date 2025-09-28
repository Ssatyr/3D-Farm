from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.base import get_db


def get_job_service(db: Session = Depends(get_db)):
    from app.services.job_service import JobService

    return JobService(db)


def get_inventory_service(db: Session = Depends(get_db)):
    from app.services.inventory_service import InventoryService

    return InventoryService(db)
