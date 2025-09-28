from fastapi import APIRouter

from app.api.v1.endpoints import inventory, jobs, printers

api_router = APIRouter()

api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(printers.router, prefix="/printers", tags=["printers"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
