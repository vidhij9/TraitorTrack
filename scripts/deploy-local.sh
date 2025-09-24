#!/bin/bash

# TraceTrack Local Deployment Script
# Deploys the application locally using Docker Compose

set -e

echo "🚀 Deploying TraceTrack locally..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✏️  Please edit .env file with your configuration before running again."
    exit 1
fi

# Create logs directory
mkdir -p logs

# Pull latest images
echo "📥 Pulling latest images..."
docker-compose pull

# Build application image
echo "🔨 Building application..."
docker compose -f docker-compose.yml -f docker-compose.local.yml build web

# Start services
echo "🚀 Starting services..."
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo "🏥 Checking service health..."
docker compose -f docker-compose.yml -f docker-compose.local.yml ps

# Show logs
echo "📋 Application logs:"
docker compose -f docker-compose.yml -f docker-compose.local.yml logs --tail=20 web

echo ""
echo "✅ TraceTrack is running locally!"
echo "🌐 Access the application at: http://localhost:5000"
echo "📊 Database: localhost:5432"
echo "🔗 Redis: localhost:6379"
echo ""
echo "Commands:"
echo "  View logs: docker compose -f docker-compose.yml -f docker-compose.local.yml logs -f"
echo "  Stop: docker compose -f docker-compose.yml -f docker-compose.local.yml down"
echo "  Restart: docker compose -f docker-compose.yml -f docker-compose.local.yml restart"