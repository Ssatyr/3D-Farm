import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/3d_ocean"

    # API
    api_v1_str: str = "/api/v1"
    project_name: str = "3D Ocean"

    # AI Detection
    failure_detection_threshold: float = 0.7
    inventory_alert_threshold: float = 0.15  # 15%
    frame_warmup_seconds: int = 10
    frame_interval_seconds: int = 30

    # File paths
    data_dir: str = "/app/data"
    logs_dir: str = "/app/logs"
    sample_images_dir: str = "/app/data/sample_images"

    class Config:
        env_file = ".env"


settings = Settings()
