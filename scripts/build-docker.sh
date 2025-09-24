#!/bin/bash

# TraceTrack Docker Build Script
# Builds production-ready Docker images

set -e

echo "🐳 Building TraceTrack Docker Images..."

# Build production image
echo "Building production image..."
docker build -t tracetrack:latest -f Dockerfile .

# Build development image
echo "Building development image..."
docker build -t tracetrack:dev -f Dockerfile.dev .

# Tag with timestamp for versioning
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker tag tracetrack:latest tracetrack:$TIMESTAMP

echo "✅ Docker images built successfully:"
echo "   - tracetrack:latest (production)"
echo "   - tracetrack:dev (development)"
echo "   - tracetrack:$TIMESTAMP (timestamped)"

# Show image sizes
echo ""
echo "📊 Image sizes:"
docker images | grep tracetrack