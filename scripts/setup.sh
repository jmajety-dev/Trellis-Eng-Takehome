#!/bin/bash
# Quick setup script for the development environment

set -e

echo "Setting up Trellis Order Lifecycle System..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Start infrastructure
echo "Starting Docker infrastructure..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 15

# Run database migrations
echo "Running database migrations..."
python scripts/migrate.py

echo "Setup complete!"
echo ""
echo "Temporal Web UI: http://localhost:8080"
echo "API Documentation: http://localhost:8000/docs (after starting API)"
echo ""
echo "Next steps:"
echo "1. Start the API server: make api"
echo "2. Run a demo workflow: make demo"
echo "3. Or start manually: make start-order"
echo ""
echo "To stop services: make down"
