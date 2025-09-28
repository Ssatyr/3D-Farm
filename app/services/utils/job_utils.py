from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def compute_material_delta(
    total_material_g: float, previous_progress: float, new_progress: float
) -> float:
    """Compute incremental material usage between two progress values (0-100)."""
    delta = max(0.0, min(100.0, new_progress)) - max(0.0, min(100.0, previous_progress))
    return float(max(0.0, (total_material_g or 0.0) * (delta / 100.0)))


def compute_remaining_needed(total_material_g: float, progress: float) -> float:
    """Compute remaining required material for a job at given progress percentage (0-100)."""
    return float(
        max(
            0.0,
            (total_material_g or 0.0) * (1.0 - max(0.0, min(100.0, progress)) / 100.0),
        )
    )


def estimate_used_on_failure_window(
    total_material_g: float,
    estimated_time_min: Optional[int],
    start_time: Optional[datetime],
    window_seconds: int = 30,
) -> float:
    """Estimate material used during the last window around failure, capped by elapsed time."""
    total_seconds = max((estimated_time_min or 60) * 60, 1)
    if start_time:
        elapsed_s = int((datetime.now(timezone.utc) - start_time).total_seconds())
        window_s = min(window_seconds, max(elapsed_s, 0))
    else:
        window_s = window_seconds
    return float(max(0.0, (total_material_g or 0.0) * (window_s / total_seconds)))
