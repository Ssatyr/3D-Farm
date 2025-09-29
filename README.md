# 3D Ocean AI Monitoring System

An AI-driven 3D printing monitoring system that provides real-time failure detection, inventory management, and job tracking.

## Features

- **AI-Powered Failure Detection**: Computer vision-based detection of print failures using OpenCV
- **Real-Time Inventory Tracking**: Monitor filament spool levels with automatic low-inventory alerts
- **Job Management**: Complete print job lifecycle management with progress tracking
- **Web Interface**: Streamlit-based dashboard for monitoring and control
- **REST API**: FastAPI-based API for system integration

## Architecture

- **Backend**: FastAPI with SQLAlchemy ORM
- **Database**: PostgreSQL with Alembic migrations
- **AI Detection**: OpenCV for computer vision analysis
- **Frontend**: Streamlit web interface
- **Containerization**: Docker with docker compose

## Quick Start

### Using Docker (Recommended)

1. **Build images:**

   ```bash
   make build
   ```

2. **Start the stack (auto-runs migrations and seeds from CSV):**

   ```bash
   make run
   ```

3. **(Optional) Generate demo images:**

   ```bash
   make samples
   ```

4. **Access the applications:**
   - API Documentation: http://localhost:8000/docs
   - Web Interface: http://localhost:8502

### Manual Setup

1. **Install dependencies:**

   ```bash
   poetry install
   ```

2. **Set up database:**

   ```bash
   # Start PostgreSQL
   docker compose up -d db

   # Run migrations
   poetry run alembic upgrade head

   # Initialize sample data
   # (generates demo images in data/sample_images)
   poetry run python scripts/init_data.py
   ```

3. **Run the application:**

   ```bash
   # Start API server
   poetry run uvicorn app.main:app --reload

   # Start web interface (in another terminal)
   poetry run streamlit run app/streamlit_app.py
   ```

## API Endpoints

### Printers

- `GET /api/v1/printers` — List active printers
- `POST /api/v1/printers` — Create new printer
- `GET /api/v1/printers/{printer_id}` — Get printer details
- `PUT /api/v1/printers/{printer_id}/status` — Update printer status
- `POST /api/v1/printers/{printer_id}/activate` — Reactivate (set to idle)

### Jobs

- `GET /api/v1/jobs` — List active jobs
- `POST /api/v1/jobs` — Create new job
- `GET /api/v1/jobs/{job_id}` — Get job by external ID
- `DELETE /api/v1/jobs/{job_id}` — Delete a queued job
- `POST /api/v1/jobs/{job_id}/start` — Start job
- `POST /api/v1/jobs/{job_id}/progress` — Update job progress
- `POST /api/v1/jobs/{job_id}/complete` — Complete job
- `POST /api/v1/jobs/{job_id}/failure-detection` — Upload image for failure detection
- `POST /api/v1/jobs/{job_id}/verify` — Verify a single frame (same as detection)
- `GET /api/v1/jobs/by-job/{job_id}/failures` — Failure events for job
- `GET /api/v1/jobs/failure-events` — All failure events (global)

### Inventory

- `GET /api/v1/inventory/spools` — List active spools
- `GET /api/v1/inventory/spools/all` — List all spools (incl. inactive)
- `GET /api/v1/inventory/spools/{spool_id}` — Get spool
- `POST /api/v1/inventory/spools` — Create new spool
- `POST /api/v1/inventory/spools/usage` — Update spool usage
- `GET /api/v1/inventory/alerts` — Active inventory alerts
- `GET /api/v1/inventory/alerts/low-inventory` — Low-inventory spools
- `POST /api/v1/inventory/alerts/{alert_id}/resolve` — Resolve alert
- `POST /api/v1/inventory/spools/{spool_id}/activate` — Reactivate spool
- `POST /api/v1/inventory/spools/{spool_id}/deactivate` — Deactivate spool

### System

- `GET /` — Root
- `GET /health` — Health check

## AI Failure Detection

The system uses computer vision to detect various types of print failures:

- **Stringing**: Detection of thin filament strings between parts
- **Layer Separation**: Identification of gaps between layers
- **Warping**: Detection of part deformation
- **Blobs/Overextrusion**: Detection of excessive material deposits

### Detection Methods

1. **Edge Detection**: Uses Canny edge detection to identify structural changes
2. **Line Detection**: Hough transform to detect stringing and layer issues
3. **Blob Detection**: Identifies overextrusion and material blobs
4. **Contour Analysis**: Analyzes part geometry for warping detection

## Web Interface

The Streamlit interface provides:

- **Dashboard**: System overview with metrics and recent activity
- **Job Management**: Create, start, and monitor print jobs
- **Failure Detection**: Upload images for AI analysis
- **Inventory Management**: Monitor spool levels and alerts
- **System Status**: Health checks and system metrics

## Configuration

Key configuration options in `app/core/config.py`:

- `failure_detection_threshold`: AI confidence threshold (default: 0.7)
- `inventory_alert_threshold`: Low inventory threshold (default: 0.15 = 15%)
- `database_url`: PostgreSQL connection string
- `data_dir`: Data directory (images, frames)
- `logs_dir`: Logs directory
- `sample_images_dir`: Directory for generated demo images
- `frame_warmup_seconds`: Delay before first frame checks
- `frame_interval_seconds`: Interval between frame checks

Environment variables can override these settings (see `.env`).

## Data Seeding

- On startup, the API seeds initial data from CSVs if present:
  - `data/seed/printers.csv`
  - `data/seed/spools.csv`
- The Docker setup mounts `./data` into the container; place CSVs there before starting.
- Demo/sample images are generated via `make samples` (or by running `scripts/init_data.py`).

## Development

### Database Migrations

```bash
# Create new migration
make migration message="Description of changes"

# Apply migrations
make migrate
```

### Code Quality

```bash
# Format code
poetry run black app/
poetry run isort app/

# Lint code
poetry run flake8 app/
```

## Project Structure

```
.
├── alembic/                 # Database migrations
├── app/
│   ├── api/                 # FastAPI endpoints
│   ├── core/                # Configuration
│   ├── db/                  # Database setup
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   └── streamlit_app.py     # Web interface
├── data/                    # Mounted data (sample_images, seed CSVs)
├── logs/                    # Logs (mounted)
├── scripts/                 # Utility scripts
├── docker-compose.yml       # Docker configuration
├── Dockerfile              # Container definition
├── Makefile                # Build automation
└── pyproject.toml          # Dependencies
```

## Makefile Commands

```bash
# Build and run
make build          # Build images
make run            # Start stack (app, db, streamlit) + follow logs
make down           # Stop stack

# Logs and status
make logs           # Tail logs
make ps             # Show service status

# Database
make migrate        # Apply migrations in running app container
make migration message="Description"  # Create new autogenerate migration

# Local (without Docker)
make install        # poetry install
make local          # uvicorn app.main:app --reload
make streamlit-local

# Utilities
make clean          # Remove containers/volumes and prune
make samples        # Generate demo images into data/sample_images
```

## Offline/Edge Deployment (Raspberry Pi)

You can run the full system locally on each printer using a Raspberry Pi so it works without a constant internet connection. The key ideas are: use local storage, run detection on-device, and sync to the cloud only when a connection is available.

### What runs on the Pi

- **API + Detection**: The FastAPI app and OpenCV-based `FailureDetector` run locally.
- **Database**: Use a lightweight local SQLite file instead of PostgreSQL.
- **Storage**: Save frames, logs, and events under the Pi’s filesystem.
- **UI (optional)**: Run the Streamlit dashboard locally for on-site monitoring.

### Important note: proposal and production detection

This offline/edge setup is a proposal. A production-ready system would likely use a more robust failure detection pipeline than the simple OpenCV heuristics used here.

- **Lightweight detectors**: Consider small object-detection models (e.g., YOLOv5n/YOLOv8n/YOLOv11n "nano/small", MobileNet-SSD, or EfficientDet-D0). Train classes like "stringing", "blob/overextrusion", and "warping". Optimize for edge (e.g., TFLite or ONNX Runtime with INT8 quantization; TensorRT on Jetson).
- **Smart image processing**: For stringing, combine morphological filtering (top-hat/black-hat), adaptive thresholding, and skeletonization to highlight thin strands; use Hough transforms for long thin lines; add simple temporal checks across frames to reduce false positives.
- **Data**: Collect a small, focused dataset from your printers and augment (lighting changes, orientations) to improve robustness.

### Minimal configuration

Configure the following environment variables for local operation (set them via your service manager or shell profile):

- DATABASE_URL: Point to a local SQLite file for the device’s database (for example, a path under the device’s data directory).
- DATA_DIR, LOGS_DIR, SAMPLE_IMAGES_DIR: Paths where frames, logs, and sample images are stored on the device.
- FRAME_INTERVAL_SECONDS: How often to capture/analyze frames; use a longer interval on small devices to reduce CPU load.
- FAILURE_DETECTION_THRESHOLD: Confidence threshold for declaring a failure; adjust based on your tolerance for false positives/negatives.

These map to settings in `app/core/config.py` and require no code changes.

### Run locally on boot

Install the required system libraries for OpenCV and Python, then install the project’s Python dependencies. Initialize the local database schema (migrations) against the SQLite file, and ensure the data and logs directories exist with correct permissions. Configure the environment variables from the "Minimal configuration" section. Finally, set up services (e.g., with `systemd`) to start the local API and, optionally, the Streamlit UI on boot, with automatic restart on failure.

For a robust setup, create `systemd` units for the API and UI so they restart automatically.

### Capturing frames without internet

- Connect a USB camera or Pi Camera and capture frames with OpenCV or a CLI (e.g., `fswebcam`).
- Save images under `DATA_DIR/frames` and call the local endpoint to analyze them:

  - `POST /api/v1/jobs/{job_id}/failure-detection` with the image file.

You can schedule this with a small Python loop, `cron`, or a `systemd` timer. Detection runs fully on-device using OpenCV, so no network is needed.

### Working offline and syncing later

- **Offline-first writes**: All jobs, failure events, and inventory updates are written to SQLite.
- **Outbox queue**: Optionally persist API calls you want to mirror to a central server into `DATA_DIR/outbox/` (JSON files). A tiny background task can retry sending when the Pi regains connectivity.
- **Conflict handling**: Use each printer’s unique `serial_no` for safe merging on the server.

### Performance and security tips

- Increase `FRAME_INTERVAL_SECONDS` and reduce image resolution to save CPU.
- Limit the API to the local network; if remote access is needed, use a VPN or reverse tunnel.
- Preload dependencies or a Docker image to avoid internet on first boot.

This approach keeps each printer autonomous: it can detect failures, log data, and display a local dashboard entirely offline, then sync when a connection is available.

## License

This project is licensed under the MIT License.
