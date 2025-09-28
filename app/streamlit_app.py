import os
import random
import time
from typing import Dict, List

import requests
import streamlit as st

from core.config import settings

# Configuration
# Default to localhost for local runs; docker-compose overrides to http://app:8000/api/v1
DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
if "api_base_url" not in st.session_state:
    st.session_state["api_base_url"] = DEFAULT_API_BASE_URL
DATA_DIR = settings.data_dir
SAMPLE_IMAGES_DIR = os.path.join(DATA_DIR, "sample_images")
WARMUP_SECONDS = settings.frame_warmup_seconds
FRAME_INTERVAL_SECONDS = settings.frame_interval_seconds

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SAMPLE_IMAGES_DIR, exist_ok=True)

st.set_page_config(page_title="3D Ocean AI Monitoring", layout="wide")

st.title("3D Ocean AI Monitoring System")
st.markdown("AI-driven 3D printing failure detection and inventory management")

# Style primary buttons as red (used for critical actions like Reactivate/Set Idle on error)
st.markdown(
    """
    <style>
    [data-testid="baseButton-primary"] {
        background-color: #d9534f !important;
        border-color: #d9534f !important;
    }
    [data-testid="baseButton-primary"]:hover {
        background-color: #c9302c !important;
        border-color: #c12e2a !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox(
    "Choose a page",
    ["Dashboard", "Job Management", "Failure Detection", "Inventory Management"],
)

# Track active page to avoid stale reruns after switching views
st.session_state["active_page"] = page

# Sidebar API settings
with st.sidebar.expander("API Settings", expanded=False):
    base_url_input = st.text_input(
        "API Base URL", value=st.session_state.get("api_base_url", DEFAULT_API_BASE_URL)
    )
    if base_url_input and base_url_input != st.session_state.get("api_base_url"):
        st.session_state["api_base_url"] = base_url_input
        st.success("API base URL updated")


def _base_candidates() -> List[str]:
    return [
        st.session_state.get("api_base_url", DEFAULT_API_BASE_URL),
        "http://localhost:8000/api/v1",
        "http://app:8000/api/v1",
    ]


def _with_bases(call):
    last_err = None
    for base in _base_candidates():
        try:
            result = call(base)
            if result is not None:
                st.session_state["api_base_url"] = base
                return result
        except Exception as e:
            last_err = str(e)
    if last_err:
        st.error(f"Connection error: {last_err}")
    return None


def _request_json(method: str, endpoint: str, data: dict | None = None) -> dict:
    def _do(base: str):
        url = f"{base}{endpoint}"
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        elif method == "DELETE":
            response = requests.delete(url)
        else:
            raise ValueError("Unsupported method")
        if response.status_code == 200:
            return response.json()
        # Surface API errors immediately and stop probing other bases
        try:
            payload = response.json()
        except Exception:
            payload = {"detail": response.text}
        msg = payload.get("detail") if isinstance(payload, dict) else str(payload)
        st.error(f"API Error: {response.status_code} - {msg}")
        return {}

    return _with_bases(_do) or {}


def _request_file(endpoint: str, files: dict) -> dict | None:
    def _do(base: str):
        url = f"{base}{endpoint}"
        response = requests.post(url, files=files)
        if response.status_code == 200:
            return response.json()
        # Surface API errors immediately and stop probing other bases
        try:
            payload = response.json()
        except Exception:
            payload = {"detail": response.text}
        msg = payload.get("detail") if isinstance(payload, dict) else str(payload)
        st.error(f"API Error: {response.status_code} - {msg}")
        return {}

    return _with_bases(_do)


def make_api_request(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    return _request_json(method, endpoint, data)


# Session state for automatic frame simulation
if "last_frame_sent_ts" not in st.session_state:
    st.session_state["last_frame_sent_ts"] = {}
if "job_started_at" not in st.session_state:
    st.session_state["job_started_at"] = {}
if "auto_simulate_frames" not in st.session_state:
    st.session_state["auto_simulate_frames"] = True


def list_sample_images() -> List[str]:
    files = []
    for name in os.listdir(SAMPLE_IMAGES_DIR):
        if name.lower().endswith((".jpg", ".jpeg", ".png")):
            files.append(os.path.join(SAMPLE_IMAGES_DIR, name))
    return files


def send_random_frame(job_id: str) -> dict:
    images = list_sample_images()
    if not images:
        # generate a couple of images if directory is empty
        create_sample_image(f"success_{int(time.time())}.jpg", is_failure=False)
        create_sample_image(f"failure_{int(time.time())}.jpg", is_failure=True)
        images = list_sample_images()
    if not images:
        return {"sent": False, "reason": "no_images"}
    # Bias towards success frames
    if random.random() < 0.9:
        candidates = [p for p in images if "success" in os.path.basename(p).lower()]
        if not candidates:
            candidates = images
    else:
        candidates = [p for p in images if "failure" in os.path.basename(p).lower()]
        if not candidates:
            candidates = images
    image_path = random.choice(candidates)
    try:
        with open(image_path, "rb") as f:
            files = {"file": f}
            result = _request_file(f"/jobs/{job_id}/verify", files)
        if result is not None:
            return {"sent": True, "result": result, "image": image_path}
        return {"sent": False, "status": "unreachable"}
    except Exception as ex:
        return {"sent": False, "error": str(ex)}


def simulate_tick_for_jobs(jobs: List[Dict]) -> None:
    """Simulate one tick: send frames and advance progress for printing jobs."""
    for job in jobs or []:
        if job.get("status") != "printing" or not st.session_state.get(
            "auto_simulate_frames", True
        ):
            continue
        now_ts = time.time()
        start_ts = st.session_state["job_started_at"].get(job.get("job_id"))
        if start_ts and (now_ts - start_ts) < WARMUP_SECONDS:
            continue
        last_ts = st.session_state["last_frame_sent_ts"].get(job.get("job_id"), 0)
        if now_ts - last_ts >= FRAME_INTERVAL_SECONDS:
            send_result = send_random_frame(job.get("job_id"))
            st.session_state["last_frame_sent_ts"][job.get("job_id")] = now_ts
            # Advance progress a bit to reflect usage
            current_progress = job.get("progress_percentage") or 0
            new_progress = min(100, current_progress + 2)
            make_api_request(
                f"/jobs/{job.get('job_id')}/progress",
                "POST",
                {"progress_percentage": new_progress},
            )


def get_printers() -> List[Dict]:
    """Get all printers, always return a list"""
    data = make_api_request("/printers")
    return data if isinstance(data, list) else []


def get_jobs() -> List[Dict]:
    """Get all active jobs, always return a list"""
    data = make_api_request("/jobs")
    return data if isinstance(data, list) else []


def get_spools() -> List[Dict]:
    """Get all spools, always return a list"""
    data = make_api_request("/inventory/spools")
    return data if isinstance(data, list) else []


def get_all_spools() -> List[Dict]:
    data = make_api_request("/inventory/spools/all")
    return data if isinstance(data, list) else []


def get_alerts() -> List[Dict]:
    """Get all alerts, always return a list"""
    data = make_api_request("/inventory/alerts")
    return data if isinstance(data, list) else []


def get_failures() -> List[Dict]:
    """Get all failure events"""
    data = make_api_request("/jobs/failure-events")
    return data if isinstance(data, list) else []


def create_sample_image(filename: str, is_failure: bool = False) -> str:
    """Create a sample image for testing"""
    import cv2
    import numpy as np

    # Create a simple image
    if is_failure:
        # Create an image with "failure" patterns (noise, lines, etc.)
        img = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
        # Add some "stringing" lines
        cv2.line(img, (100, 100), (500, 200), (255, 255, 255), 2)
        cv2.line(img, (200, 300), (400, 100), (255, 255, 255), 2)
    else:
        # Create a clean image
        img = np.zeros((400, 600, 3), dtype=np.uint8)
        # Add a simple "print" shape
        cv2.rectangle(img, (200, 150), (400, 350), (100, 100, 100), -1)

    filepath = os.path.join(SAMPLE_IMAGES_DIR, filename)
    cv2.imwrite(filepath, img)
    # Remember last generated image for test run
    st.session_state["last_generated_image_path"] = filepath
    return filepath


# Dashboard Page
if page == "Dashboard":
    st.header("System Dashboard")

    col0, col1, col2, col3, col4 = st.columns(5)

    # Get system data
    # Fetch fresh data
    printers = get_printers()
    jobs = get_jobs()
    # Simulate one tick so dashboard reflects live changes even if user stays on this page
    simulate_tick_for_jobs(jobs)
    # Fetch again after tick
    printers = get_printers()
    jobs = get_jobs()
    spools = get_all_spools()
    alerts = get_alerts()

    with col0:
        st.metric("Total Printers", len(printers))

    with col1:
        st.metric(
            "Active Printers",
            len([p for p in printers if p.get("status") == "printing"]),
        )

    with col2:
        st.metric(
            "Active Jobs", len([j for j in jobs if j.get("status") == "printing"])
        )

    with col3:
        st.metric("Total Spools", len(spools))

    with col4:
        st.metric("Active Alerts", len(alerts))

    # Summary of unavailable resources (exclude maintenance category)
    unavailable_printers = [p for p in printers if p.get("status") in ["error"]]
    unavailable_spools = [s for s in spools if not s.get("is_active")]
    st.info(
        f"Unavailable due to failure - Printers: {len(unavailable_printers)} | Spools: {len(unavailable_spools)}"
    )

    # Printer status distribution chart
    st.subheader("Printer Status Distribution")
    status_counts = {
        "idle": len([p for p in printers if p.get("status") == "idle"]),
        "printing": len([p for p in printers if p.get("status") == "printing"]),
        "error": len([p for p in printers if p.get("status") == "error"]),
    }
    chart_data = [
        {"status": k, "count": v}
        for k, v in status_counts.items()
        if k != "maintenance"
    ]
    chart_spec = {
        "data": {"values": chart_data},
        "mark": {"type": "arc", "innerRadius": 50},
        "encoding": {
            "theta": {"field": "count", "type": "quantitative"},
            "color": {
                "field": "status",
                "type": "nominal",
                "sort": ["idle", "printing", "error"],
            },
            "tooltip": [
                {"field": "status", "type": "nominal"},
                {"field": "count", "type": "quantitative"},
            ],
        },
    }
    chart_placeholder = st.empty()
    chart_placeholder.vega_lite_chart(chart_spec, use_container_width=True)

    # Recent activity
    st.subheader("Recent Activity")
    if jobs:
        for job in jobs[:5]:
            st.write(
                f"Job {job.get('job_id', 'N/A')} - {job.get('part_name', 'N/A')} (status: {job.get('status', 'unknown')})"
            )
    else:
        st.info("No active jobs")

    # Alerts panel (visible list)
    st.subheader("Alerts")
    alerts = get_alerts()
    if alerts:
        for alert in alerts:
            st.warning(alert.get("message"))
    else:
        st.success("No active alerts")

    # Failure log
    st.subheader("Failure Log")
    failures = get_failures()
    if failures:
        for ev in sorted(
            failures, key=lambda e: e.get("detected_at") or "", reverse=True
        )[:10]:
            st.write(
                f"{ev.get('detected_at', '')}: JobID={ev.get('job_id')} Type={ev.get('failure_type')} Confidence={ev.get('confidence_score', 0):.2f}"
            )
    else:
        st.info("No failures detected yet")

    # Resource management (Printers and Spools side by side)
    st.subheader("Resources")
    colA, colB = st.columns(2)
    with colA:
        st.write("Printers")
        for p in printers:
            pc1, pc2 = st.columns([3, 1])
            with pc1:
                st.write(
                    f"{p.get('machine_name')} (ID: {p.get('id')}) — Status: {p.get('status')}"
                )
            with pc2:
                if p.get("status") != "idle":
                    is_error = p.get("status") == "error"
                    if st.button(
                        "Set Idle",
                        key=f"set_idle_{p.get('id')}",
                        type="primary" if is_error else "secondary",
                    ):
                        make_api_request(
                            f"/printers/{p.get('id')}/activate", method="POST"
                        )
                        st.rerun()
    with colB:
        st.write("Spools")
        for s in spools:
            sc1, sc2 = st.columns([3, 1])
            with sc1:
                st.write(
                    f"{s.get('spool_id')} ({s.get('material_type')}, {s.get('color')}) — Active: {s.get('is_active')}"
                )
            with sc2:
                if not s.get("is_active"):
                    if st.button(
                        "Reactivate",
                        key=f"react_{s.get('id')}",
                        type="primary",
                    ):
                        make_api_request(
                            f"/inventory/spools/{s.get('spool_id')}/activate",
                            method="POST",
                        )
                        st.rerun()
                else:
                    if st.button("Deactivate", key=f"deact_{s.get('id')}"):
                        make_api_request(
                            f"/inventory/spools/{s.get('spool_id')}/deactivate",
                            method="POST",
                        )
                        st.rerun()

    # Auto-refresh dashboard (including spool inventory) on interval
    snapshot = st.session_state.get("active_page")
    time.sleep(FRAME_INTERVAL_SECONDS)
    if (
        st.session_state.get("active_page") == "Dashboard"
        and st.session_state.get("active_page") == snapshot
    ):
        st.rerun()

# Job Management Page
elif page == "Job Management":
    st.header("Job Management")

    # Create new job
    with st.expander("Create New Job", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            printers = [p for p in get_printers() if p.get("status") == "idle"]
            if not printers:
                st.info("No printers found. Create a sample printer to proceed.")
                if st.button("Create Sample Printer"):
                    sample_payload = {
                        "serial_no": f"SN-{int(time.time())}",
                        "machine_name": "Printer-1",
                        "location": "Lab",
                        "model": "Generic",
                        "max_bed_temp": 100.0,
                        "max_nozzle_temp": 260.0,
                    }
                    make_api_request("/printers", method="POST", data=sample_payload)
                    st.rerun()

            printers = [p for p in get_printers() if p.get("status") == "idle"]
            selected_printer = (
                st.selectbox(
                    "Select Printer",
                    printers,
                    format_func=lambda p: f"{p.get('machine_name')} ({p.get('serial_no')})"
                    if isinstance(p, dict)
                    else str(p),
                )
                if printers
                else None
            )
            printer_id = (
                selected_printer.get("id")
                if isinstance(selected_printer, dict)
                else None
            )

            part_name = st.text_input("Part Name", value="Sample Part")
            part_description = st.text_area(
                "Part Description", value="A sample 3D printed part"
            )
            batch = st.text_input("Batch", value="BATCH-001")
            operator = st.text_input("Operator", value="AI System")

        with col2:
            estimated_time = st.number_input(
                "Estimated Time (minutes)", min_value=1, value=60
            )
            material_g = st.number_input(
                "Material Weight (g)", min_value=0.1, value=50.0
            )
            spools = get_spools()
            # Show all spools; warn if insufficient/ inactive
            available_spools = spools
            selected_spool = (
                st.selectbox(
                    "Select Spool",
                    available_spools,
                    format_func=lambda s: f"{s.get('spool_id')} ({s.get('material_type')}, {s.get('color')}) - {s.get('remaining_weight_g', 0):.1f}g left",
                )
                if available_spools
                else None
            )
            spool_id = (
                selected_spool.get("spool_id")
                if isinstance(selected_spool, dict)
                else None
            )
            total_layers = st.number_input("Total Layers", min_value=1, value=100)

        create_disabled = printer_id is None
        if st.button("Create Job", disabled=create_disabled):
            job_data = {
                "printer_id": printer_id,
                "part_name": part_name,
                "part_description": part_description,
                "batch": batch,
                "operator": operator,
                "estimated_time_min": estimated_time,
                "material_g": material_g,
                "spool_id": spool_id,
                "total_layers": total_layers,
            }

            result = make_api_request("/jobs", "POST", job_data)
            if result:
                st.success(f"Job created: {result.get('job_id', 'N/A')}")
                st.rerun()
        if printer_id is None:
            st.warning("Select a printer before creating a job.")
        if spool_id is None and material_g > 0:
            st.warning(
                "Select a spool (insufficient material will be enforced at start time)."
            )
        if selected_spool and not selected_spool.get("is_active"):
            st.warning(
                "Selected spool is inactive and will block start until reactivated."
            )
        if selected_printer and selected_printer.get("status") == "printing":
            st.info(
                "Selected printer is currently busy; job will remain queued until it becomes idle."
            )
        # Spool in-use hint at creation time
        if selected_spool and selected_spool.get("spool_id"):
            jobs_for_hint = get_jobs()
            in_use_job = next(
                (
                    j
                    for j in jobs_for_hint
                    if j.get("spool_id") == selected_spool.get("spool_id")
                    and j.get("status") == "printing"
                ),
                None,
            )
            if in_use_job:
                st.info(
                    f"Selected spool is currently in use by job {in_use_job.get('job_id')}; this job will queue."
                )

    # Active jobs
    st.subheader("Active Jobs")
    jobs = get_jobs()

    # Auto-send frames toggle
    st.checkbox(
        "Auto-send frames every 30s for printing jobs",
        key="auto_simulate_frames",
        value=True,
    )

    if jobs:
        for job in jobs:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                with col1:
                    st.write(
                        f"**{job.get('part_name', 'N/A')}** ({job.get('job_id', 'N/A')})"
                    )
                    st.write(f"Status: {job.get('status', 'unknown')}")
                    st.write(f"Printer ID: {job.get('printer_id', 'N/A')}")
                    if job.get("spool_id"):
                        st.write(
                            f"Spool: {job.get('spool_id')} ({job.get('material_g', 0)}g)"
                        )
                    # Availability hints
                    prn = next(
                        (p for p in printers if p.get("id") == job.get("printer_id")),
                        None,
                    )
                    if (
                        prn
                        and prn.get("status") == "printing"
                        and job.get("status") == "queued"
                    ):
                        st.info("Printer currently in use by another job")
                    if job.get("spool_id"):
                        sp = next(
                            (
                                s
                                for s in spools
                                if s.get("spool_id") == job.get("spool_id")
                            ),
                            None,
                        )
                        if (
                            sp
                            and not sp.get("is_active")
                            and job.get("status") == "queued"
                        ):
                            st.warning(
                                "Selected spool is inactive; job cannot start until reactivated"
                            )
                        # Spool in-use hint for queued jobs
                        if sp and job.get("status") == "queued":
                            other_job = next(
                                (
                                    j
                                    for j in jobs
                                    if j.get("spool_id") == job.get("spool_id")
                                    and j.get("status") == "printing"
                                    and j.get("job_id") != job.get("job_id")
                                ),
                                None,
                            )
                            if other_job:
                                st.info(
                                    f"Spool currently in use by job {other_job.get('job_id')}"
                                )
                    if job.get("progress_percentage"):
                        st.progress(job.get("progress_percentage", 0) / 100)

                with col2:
                    if job.get("status") == "queued":
                        if st.button(f"Start", key=f"start_{job.get('id')}"):
                            make_api_request(f"/jobs/{job.get('job_id')}/start", "POST")
                            st.session_state["job_started_at"][
                                job.get("job_id")
                            ] = time.time()
                            st.rerun()
                        if st.button("Delete", key=f"del_{job.get('id')}"):
                            make_api_request(f"/jobs/{job.get('job_id')}", "DELETE")
                            st.rerun()

                with col3:
                    if job.get("status") == "printing":
                        if st.button(f"Complete", key=f"complete_{job.get('id')}"):
                            make_api_request(
                                f"/jobs/{job.get('job_id')}/complete", "POST"
                            )
                            st.rerun()

                with col4:
                    if job.get("status") == "printing":
                        if st.button(f"Fail", key=f"fail_{job.get('id')}"):
                            make_api_request(
                                f"/jobs/{job.get('job_id')}/complete?success=false",
                                "POST",
                            )
                            st.rerun()

                # Automatic frame sending while printing
                if job.get("status") == "printing" and st.session_state.get(
                    "auto_simulate_frames", True
                ):
                    now_ts = time.time()
                    # Short warmup window to avoid instant false positives
                    start_ts = st.session_state["job_started_at"].get(job.get("job_id"))
                    if start_ts and (now_ts - start_ts) < WARMUP_SECONDS:
                        st.info("Auto frames starting shortly...")
                        st.divider()
                        continue
                    last_ts = st.session_state["last_frame_sent_ts"].get(
                        job.get("job_id"), 0
                    )
                    if now_ts - last_ts >= FRAME_INTERVAL_SECONDS:
                        send_result = send_random_frame(job.get("job_id"))
                        st.session_state["last_frame_sent_ts"][
                            job.get("job_id")
                        ] = now_ts
                        if send_result.get("sent"):
                            result = send_result.get("result", {})
                            if result.get("failure_detected"):
                                st.warning(
                                    f"Failure detected for {job.get('job_id')} ({result.get('failure_type')})"
                                )
                            else:
                                st.info(
                                    f"Frame sent for {job.get('job_id')}: no failure detected"
                                )
                            # Update job progress by small step to reflect material usage
                            current_progress = job.get("progress_percentage") or 0
                            new_progress = min(100, current_progress + 2)
                            make_api_request(
                                f"/jobs/{job.get('job_id')}/progress",
                                "POST",
                                {"progress_percentage": new_progress},
                            )
                        else:
                            st.info("Frame not sent (no images or error)")

                st.divider()

    # Auto-refresh when auto-simulating
    if st.session_state.get("auto_simulate_frames", True) and any(
        j.get("status") == "printing" for j in jobs or []
    ):
        snapshot = st.session_state.get("active_page")
        time.sleep(FRAME_INTERVAL_SECONDS)
        if (
            st.session_state.get("active_page") == "Job Management"
            and st.session_state.get("active_page") == snapshot
        ):
            st.rerun()
    else:
        st.info("No active jobs")

# Failure Detection Page
elif page == "Failure Detection":
    st.header("AI Failure Detection")

    # Simulate failure detection
    st.subheader("Simulate Failure Detection")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Test with Sample Images**")

        if st.button("Generate Success Image"):
            filename = f"success_{int(time.time())}.jpg"
            filepath = create_sample_image(filename, is_failure=False)
            st.success(f"Created success image: {filename}")
            st.image(filepath, caption="Success Image", width=300)

        if st.button("Generate Failure Image"):
            filename = f"failure_{int(time.time())}.jpg"
            filepath = create_sample_image(filename, is_failure=True)
            st.success(f"Created failure image: {filename}")
            st.image(filepath, caption="Failure Image", width=300)

    with col2:
        st.write("**Test with Active Job**")
        jobs = get_jobs()
        printing_jobs = [j for j in jobs if j.get("status") == "printing"]

        if printing_jobs:
            selected_job = st.selectbox(
                "Select Job",
                printing_jobs,
                format_func=lambda x: f"{x.get('job_id')} - {x.get('part_name')}",
            )

            if st.button("Test Failure Detection"):
                # Use the last generated image if available; otherwise create one
                test_filepath = st.session_state.get("last_generated_image_path")
                if not test_filepath or not os.path.exists(test_filepath):
                    test_filename = f"test_failure_{int(time.time())}.jpg"
                    test_filepath = create_sample_image(test_filename, is_failure=True)

                # Upload and test using resilient base URL logic
                result = None
                with open(test_filepath, "rb") as f:
                    files = {"file": f}
                    result = _request_file(
                        f"/jobs/{selected_job.get('job_id')}/failure-detection", files
                    )

                if result is not None:
                    if result.get("failure_detected"):
                        st.error(
                            f"Failure Detected: {result.get('failure_type')} (Confidence: {result.get('confidence', 0):.2f})"
                        )
                    else:
                        st.success("No failure detected")
                else:
                    st.error("API Error: failure detection endpoint unreachable")
        else:
            st.info("No printing jobs available for testing")

    # Failure history
    st.subheader("Recent Failure Events")
    events = get_failures()
    if events:
        for ev in sorted(
            events, key=lambda e: e.get("detected_at") or "", reverse=True
        )[:20]:
            st.write(
                f"{ev.get('detected_at','')}: JobID={ev.get('job_id')} | Type={ev.get('failure_type')} | Confidence={ev.get('confidence_score',0):.2f}"
            )
    else:
        st.info("No failure events yet")

# Inventory Management Page
elif page == "Inventory Management":
    st.header("Inventory Management")

    # Create new spool
    with st.expander("Add New Spool", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            spool_id = st.text_input("Spool ID", value=f"SPOOL-{int(time.time())}")
            material_type = st.selectbox(
                "Material Type", ["PLA", "ABS", "PETG", "TPU", "Other"]
            )
            total_weight = st.number_input(
                "Total Weight (g)", min_value=1.0, value=1000.0
            )

        with col2:
            color = st.text_input("Color", value="White")
            brand = st.text_input("Brand", value="Generic")

        if st.button("Add Spool"):
            spool_data = {
                "spool_id": spool_id,
                "material_type": material_type,
                "total_weight_g": total_weight,
                "color": color,
                "brand": brand,
            }

            result = make_api_request("/inventory/spools", "POST", spool_data)
            if result:
                st.success(f"Spool added: {spool_id}")
                st.rerun()

    # Spool inventory
    st.subheader("Spool Inventory")
    spools = get_all_spools()

    if spools:
        for spool in spools:
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

            with col1:
                st.write(
                    f"**{spool.get('spool_id')}** - {spool.get('material_type')} ({spool.get('color')})"
                )
                remaining = spool.get("remaining_weight_g", 0)
                total = spool.get("total_weight_g", 1)
                percentage = (remaining / total) * 100 if total > 0 else 0
                st.progress(percentage / 100)
                st.write(f"{remaining:.1f}g / {total:.1f}g ({percentage:.1f}%)")

            with col2:
                if spool.get("is_low_inventory"):
                    st.warning("Low")
                else:
                    st.success("OK")

            with col3:
                if st.button("Use 10g", key=f"use_{spool.get('id')}"):
                    make_api_request(
                        "/inventory/spools/usage",
                        "POST",
                        {"spool_id": spool.get("spool_id"), "material_used_g": 10.0},
                    )
                    st.rerun()

            with col4:
                if st.button("Use 50g", key=f"use50_{spool.get('id')}"):
                    make_api_request(
                        "/inventory/spools/usage",
                        "POST",
                        {"spool_id": spool.get("spool_id"), "material_used_g": 50.0},
                    )
                    st.rerun()
            # Activation toggles are only shown on the Dashboard view

            st.divider()
    else:
        st.info("No spools in inventory")

    # Add new printer
    st.subheader("Add New Printer")
    with st.form("add_printer_form"):
        p_serial = st.text_input("Serial Number", value=f"SN-{int(time.time())}")
        p_name = st.text_input("Machine Name", value="Printer-2")
        p_location = st.text_input("Location", value="Lab")
        p_model = st.text_input("Model", value="Generic")
        p_bed = st.number_input("Max Bed Temp", min_value=0.0, value=100.0)
        p_nozzle = st.number_input("Max Nozzle Temp", min_value=0.0, value=260.0)
        submitted = st.form_submit_button("Add Printer")
        if submitted:
            payload = {
                "serial_no": p_serial,
                "machine_name": p_name,
                "location": p_location,
                "model": p_model,
                "max_bed_temp": p_bed,
                "max_nozzle_temp": p_nozzle,
            }
            res = make_api_request("/printers", method="POST", data=payload)
            if res:
                st.success("Printer added")
                st.rerun()

    # Alerts
    st.subheader("Inventory Alerts")
    alerts = get_alerts()

    if alerts:
        for alert in alerts:
            st.warning(alert.get("message"))
    else:
        st.success("No active alerts")

    # Auto-refresh inventory section on interval
    snapshot = st.session_state.get("active_page")
    time.sleep(FRAME_INTERVAL_SECONDS)
    if (
        st.session_state.get("active_page") == "Inventory Management"
        and st.session_state.get("active_page") == snapshot
    ):
        st.rerun()

    # API Health Check quick indicator
    st.subheader("API Status")
    try:
        health_ok = False
        for base in [
            st.session_state.get("api_base_url", DEFAULT_API_BASE_URL),
            "http://localhost:8000/api/v1",
            "http://app:8000/api/v1",
        ]:
            root = base.replace("/api/v1", "")
            try:
                response = requests.get(f"{root}/health")
                if response.status_code == 200:
                    st.session_state["api_base_url"] = base
                    st.success("API is healthy")
                    health_ok = True
                    break
            except Exception:
                continue
        if not health_ok:
            st.error("Cannot connect to API")
    except Exception:
        st.error("Cannot connect to API")

    # Footer
    st.markdown("---")
    st.markdown(
        "**3D Ocean AI Monitoring System** - Built with FastAPI, Streamlit, and OpenCV"
    )
