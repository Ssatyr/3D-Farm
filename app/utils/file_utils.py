import os
import uuid
from typing import Optional


def save_upload_to_data(
    file_obj,
    base_dir: str,
    job_id: Optional[str] = None,
    subdir: str = "",
) -> str:
    """Save an uploaded file-like object to the data directory and return the path.

    Parameters
    ----------
    file_obj: file-like object with .filename and .file (e.g., FastAPI UploadFile)
    base_dir: base data directory (e.g., settings.data_dir)
    job_id: optional job identifier to prefix filenames
    subdir: optional subdirectory within base_dir
    """
    filename = getattr(file_obj, "filename", None) or "frame.jpg"
    _, ext = os.path.splitext(filename)
    unique = uuid.uuid4().hex[:8]
    safe_prefix = f"{job_id}_" if job_id else ""
    out_name = f"{safe_prefix}{unique}{ext or '.jpg'}"

    target_dir = os.path.join(base_dir, subdir) if subdir else base_dir
    os.makedirs(target_dir, exist_ok=True)
    out_path = os.path.join(target_dir, out_name)

    with open(out_path, "wb") as buffer:
        # FastAPI UploadFile has .file, but allow raw file-like too
        src = getattr(file_obj, "file", None) or file_obj
        buffer.write(src.read())

    return out_path
