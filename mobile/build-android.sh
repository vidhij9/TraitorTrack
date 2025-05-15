#!/bin/bash

# TraceTrack Android build script
echo "=== TraceTrack Android App Builder ==="
echo "Building Android app for TraceTrack"

# Set variables
APP_DIR=$(dirname "$0")
OUTPUT_DIR="$APP_DIR/android"

# Ensure Capacitor is installed
echo "Checking Capacitor installation..."
if [ ! -d "node_modules/@capacitor" ]; then
  echo "Installing Capacitor packages..."
  npm install @capacitor/core @capacitor/cli @capacitor/android @capacitor/camera
fi

# Create android directory if it doesn't exist
if [ ! -d "$OUTPUT_DIR" ]; then
  echo "Creating Android project..."
  npx cap add android
else
  echo "Android project already exists"
fi

# Copy web assets
echo "Copying web assets to Android project..."
npx cap copy android

# Update plugins
echo "Updating Android plugins..."
npx cap update android

# Open Android Studio (optional)
if [ "$1" == "--open" ]; then
  echo "Opening Android Studio..."
  npx cap open android
fi

echo "Build preparation complete!"
echo "To build the APK, run: 'npx cap open android' and use Build > Build Bundle(s) / APK(s) > Build APK(s)"
echo "====================================="