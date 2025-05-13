# TraceTrack Mobile App

This directory contains the necessary files to build a native Android application for the TraceTrack system using Capacitor.

## Prerequisites

- Node.js and npm
- Android Studio (for building and deploying the Android app)
- Android SDK (usually installed with Android Studio)
- JDK (Java Development Kit) 11 or newer

## Setup

1. Make sure you have installed all prerequisites
2. Run the setup script:
   ```
   ./setup-android.sh
   ```

This will:
- Install necessary dependencies
- Copy web assets from the main application
- Initialize the Capacitor Android project

## Building the Android App

After setup, you can build the Android application:

1. Run the build script:
   ```
   ./build-android.sh
   ```

2. Open the project in Android Studio:
   ```
   npx cap open android
   ```

3. In Android Studio, you can:
   - Build and run the app on an emulator
   - Build and run the app on a connected device
   - Generate a signed APK for distribution

## Manual Build Steps

If you prefer to run each step manually:

1. Install dependencies:
   ```
   npm install
   ```

2. Add the Android platform:
   ```
   npx cap add android
   ```

3. Copy and sync web assets:
   ```
   npx cap sync
   ```

4. Open in Android Studio:
   ```
   npx cap open android
   ```

## Customization

- App icons: Replace files in `android/app/src/main/res/mipmap-*`
- Splash screen: Modify files in `android/app/src/main/res/drawable-*`
- App name: Edit `android/app/src/main/res/values/strings.xml`
- App theme colors: Edit `android/app/src/main/res/values/colors.xml`

## Troubleshooting

Common issues:

1. **Build errors**: Make sure you have the latest Android SDK and build tools installed.
2. **Capacitor not found**: Check that you've installed the npm dependencies.
3. **App crashes on launch**: Check the logs in Android Studio for details.
4. **Camera not working**: Ensure camera permissions are properly set in AndroidManifest.xml.

## QR Code Scanning

The mobile app enhances QR code scanning capabilities by using the native device camera through the Capacitor Camera plugin. This provides better performance and reliability compared to web-based scanning.