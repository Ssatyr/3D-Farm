import logging
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np

from app.core.config import settings
from app.services.utils.detection_utils import (
    detect_blobs,
    detect_layer_separation,
    detect_stringing,
    detect_warping,
)

logger = logging.getLogger(__name__)


class FailureDetector:
    def __init__(self):
        self.threshold = settings.failure_detection_threshold
        self.sample_images_dir = Path(settings.sample_images_dir)
        self.sample_images_dir.mkdir(parents=True, exist_ok=True)

    def detect_failure(self, image_path: str, job_id: str) -> Tuple[bool, float, str]:
        """
        Detect print failure from camera image.
        Returns: (is_failure, confidence, failure_type)
        """
        try:
            # Load and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Could not load image: {image_path}")
                return False, 0.0, "image_load_error"

            # Convert to grayscale for analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply multiple detection methods
            results = [
                ("stringing", detect_stringing(gray)),
                ("layer_separation", detect_layer_separation(gray)),
                ("warping", detect_warping(gray)),
                ("blob", detect_blobs(gray)),
            ]

            # Find the highest confidence failure
            max_confidence = 0.0
            failure_type = "none"

            for failure_type_name, confidence in results:
                if confidence > max_confidence:
                    max_confidence = confidence
                    failure_type = failure_type_name

            is_failure = max_confidence > self.threshold

            logger.info(
                f"Failure detection for job {job_id}: {failure_type} with confidence {max_confidence:.2f}"
            )

            return is_failure, max_confidence, failure_type

        except Exception as e:
            logger.error(f"Error in failure detection: {str(e)}")
            return False, 0.0, "detection_error"

    def save_sample_image(self, image: np.ndarray, filename: str) -> str:
        """Save a sample image for training/testing"""
        filepath = self.sample_images_dir / filename
        cv2.imwrite(str(filepath), image)
        return str(filepath)

    def get_sample_images(self) -> List[str]:
        """Get list of sample images"""
        if not self.sample_images_dir.exists():
            return []

        image_files = []
        for ext in ["*.jpg", "*.jpeg", "*.png"]:
            image_files.extend(self.sample_images_dir.glob(ext))

        return [str(f) for f in image_files]
