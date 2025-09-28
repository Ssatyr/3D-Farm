#!/bin/bash

echo "🌊 Starting 3D Ocean AI Monitoring System Demo"
echo "=============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "📦 Building and starting services..."
make build
make run

echo "⏳ Waiting for services to start..."
sleep 10

echo "🗄️ Setting up database..."
make setup-db

echo "📊 Initializing sample data..."
docker compose exec app python scripts/init_data.py

echo "🧪 Running system tests..."
docker compose exec app python scripts/test_system.py

echo ""
echo "✅ System is ready!"
echo ""
echo "🌐 Access the applications:"
echo "   - API Documentation: http://localhost:8000/docs"
echo "   - Web Interface: http://localhost:8502"
echo ""
echo "📋 Available commands:"
echo "   - View logs: docker compose logs -f"
echo "   - Stop system: make clean"
echo "   - Restart: make run"
echo ""
echo "🎯 Try the web interface to:"
echo "   - Create and manage print jobs"
echo "   - Test AI failure detection"
echo "   - Monitor inventory levels"
echo "   - View system status"
