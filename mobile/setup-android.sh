#!/bin/bash

echo "Setting up TraceTrack Android app..."

# Navigate to the mobile directory
cd "$(dirname "$0")"

# Make sure node modules are installed
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Create necessary directories
mkdir -p www/css www/js www/img

# Copy the web app's static assets to the www directory
echo "Copying web assets..."
cp -r ../static/css/* www/css/
cp -r ../static/js/* www/js/
cp -r ../static/img/* www/img/

# Copy manifest and service worker
cp ../static/manifest.json www/
cp ../static/service-worker.js www/

# Run the capacitor initialization script
echo "Initializing Capacitor..."
node init-capacitor.js

echo "Setup complete! You can now build the Android app."