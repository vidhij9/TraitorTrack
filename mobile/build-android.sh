#!/bin/bash

echo "Building TraceTrack Android app..."

# Navigate to the mobile directory
cd "$(dirname "$0")"

# Make sure setup has been run
if [ ! -d "android" ]; then
  echo "Android platform not found. Running setup first..."
  ./setup-android.sh
fi

# Ensure latest static assets are copied
echo "Updating static assets..."
mkdir -p www/css www/js www/img
cp -r ../static/css/* www/css/
cp -r ../static/js/* www/js/
cp -r ../static/img/* www/img/
cp ../static/manifest.json www/
cp ../static/service-worker.js www/

# Sync changes to Android project
echo "Syncing with Android project..."
npx cap sync android

echo "Build preparation complete!"
echo "To open Android Studio and continue building:"
echo "  1. Install Android Studio"
echo "  2. Run: npx cap open android"
echo "  3. Use Android Studio to build and deploy the app"
echo ""
echo "To generate an APK directly (if Android Studio CLI tools are available):"
echo "  cd android && ./gradlew assembleDebug"
echo ""
echo "The APK will be located at: android/app/build/outputs/apk/debug/app-debug.apk"