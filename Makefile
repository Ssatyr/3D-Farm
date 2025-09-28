.PHONY: build run dev test clean setup-db migrate

# Build the Docker image
build:
	docker compose build

# Run the application
run:
	docker compose up -d
	@echo "API: http://localhost:8000/docs"
	@echo "Web: http://localhost:8502"
	@echo "Following logs (Ctrl+C to stop; services continue running)..."
	docker compose logs -f

# Stop the application
down:
	docker compose down

# Run in development mode
dev:
	docker compose up

logs:
	docker compose logs -f

ps:
	docker compose ps


# Clean up containers and volumes
clean:
	docker compose down -v
	docker system prune -f

# Setup database and run migrations
setup-db:
	docker compose up -d db
	sleep 10
	docker compose exec app alembic upgrade head

# Run database migrations
migrate:
	docker compose exec app alembic upgrade head

# Create new migration
migration:
	docker compose exec app alembic revision --autogenerate -m "$(message)"

# Install dependencies locally
install:
	poetry install

# Run locally
local:
	poetry run uvicorn app.main:app --reload

# Run streamlit locally
streamlit-local:
	poetry run streamlit run app/streamlit_app.py

# Generate and rate sample images
samples:
	docker compose exec app python scripts/init_data.py
