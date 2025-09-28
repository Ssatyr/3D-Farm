#!/usr/bin/env python3
"""
Initialize the database with sample data
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from app.db.base import SessionLocal, engine
from app.models.printer import Printer
from app.models.job import PrintJob
from app.models.inventory import Spool
from app.db.base import Base
import cv2
import numpy as np
from datetime import datetime, timedelta

# scripts/init_data.py
import os
import random
from pathlib import Path

import cv2
import numpy as np

SAMPLE_DIR = Path(os.environ.get("SAMPLE_IMAGES_DIR", "/app/data/sample_images"))


def generate_image(is_failure: bool) -> np.ndarray:
    if is_failure:
        img = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
        # Add noisy lines
        for _ in range(8):
            p1 = (random.randint(0, 599), random.randint(0, 399))
            p2 = (random.randint(0, 599), random.randint(0, 399))
            cv2.line(img, p1, p2, (255, 255, 255), 2)
        # Add blobs
        for _ in range(5):
            center = (random.randint(50, 550), random.randint(50, 350))
            radius = random.randint(10, 30)
            cv2.circle(img, center, radius, (255, 255, 255), -1)
    else:
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        cv2.rectangle(img, (200, 150), (400, 350), (100, 100, 100), -1)
        # Add subtle texture
        for _ in range(200):
            x, y = random.randint(0, 599), random.randint(0, 399)
            img[y, x] = (100, 100, 100)
    return img


essential = {
    "success": 20,
    "failure": 20,
}


def rate_image(img: np.ndarray) -> float:
    # Simple heuristic score: edges + blobs ~ failure probability
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_ratio = edges.mean() / 255.0
    return min(max(edge_ratio, 0.0), 1.0)


def main():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    for label, count in essential.items():
        for i in range(count):
            is_failure = label == "failure"
            img = generate_image(is_failure)
            score = rate_image(img)
            fn = f"{label}_{i:03d}_{int(score * 100)}.jpg"
            cv2.imwrite(str(SAMPLE_DIR / fn), img)
    print(f"Generated sample images in {SAMPLE_DIR}")


if __name__ == "__main__":
    main()
