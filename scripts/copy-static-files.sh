#!/bin/bash

# Script to copy static files from application container to shared volume
# This ensures nginx can serve static files directly in production

set -e

echo "📁 Copying static files to shared volume..."

# Create temporary container to copy static files
TEMP_CONTAINER=$(docker create tracetrack:latest)

# Copy static files from container to host
mkdir -p ./static-temp
docker cp $TEMP_CONTAINER:/app/static/. ./static-temp/

# Copy to the volume used by nginx
if docker volume ls | grep -q "static_files"; then
    echo "✅ Using existing static_files volume"
else
    echo "📦 Creating static_files volume"
    docker volume create static_files
fi

# Use a helper container to copy files to the volume
docker run --rm \
    -v "$(pwd)/static-temp:/source:ro" \
    -v "static_files:/target" \
    alpine:latest \
    sh -c "cp -r /source/* /target/"

# Cleanup
docker rm $TEMP_CONTAINER
rm -rf ./static-temp

echo "✅ Static files copied successfully to shared volume"