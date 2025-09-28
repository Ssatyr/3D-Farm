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

## License

This project is licensed under the MIT License.
