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

1. **Build and run the system:**

   ```bash
   make build
   make run
   ```

2. **Initialize the database:**

   ```bash
   make setup-db
   ```

3. **Access the applications:**
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

- `GET /api/v1/printers` - List all printers
- `POST /api/v1/printers` - Create new printer
- `GET /api/v1/printers/{id}` - Get printer details
- `PUT /api/v1/printers/{id}/status` - Update printer status

### Jobs

- `GET /api/v1/jobs` - List active jobs
- `POST /api/v1/jobs` - Create new job
- `POST /api/v1/jobs/{id}/start` - Start job
- `POST /api/v1/jobs/{id}/progress` - Update job progress
- `POST /api/v1/jobs/{id}/complete` - Complete job
- `POST /api/v1/jobs/{id}/failure-detection` - Upload image for failure detection

### Inventory

- `GET /api/v1/inventory/spools` - List all spools
- `POST /api/v1/inventory/spools` - Create new spool
- `POST /api/v1/inventory/spools/usage` - Update spool usage
- `GET /api/v1/inventory/alerts` - Get inventory alerts

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
- `data_dir`: Directory for storing images and logs

## Development

### Database Migrations

```bash
# Create new migration
make migration message="Description of changes"

# Apply migrations
make migrate
```

### Testing

```bash
make test
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
│   ├── schemas/              # Pydantic schemas
│   ├── services/            # Business logic
│   └── streamlit_app.py     # Web interface
├── scripts/                 # Utility scripts
├── docker compose.yml       # Docker configuration
├── Dockerfile              # Container definition
├── Makefile                # Build automation
└── pyproject.toml          # Dependencies
```

## License

This project is licensed under the MIT License.
