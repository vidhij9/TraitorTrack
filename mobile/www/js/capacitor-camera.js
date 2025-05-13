// This file provides native camera integration for QR scanning
// when running in the Capacitor native app environment

import { Camera } from '@capacitor/camera';
import { Capacitor } from '@capacitor/core';

// Function to check if the app is running in a Capacitor environment
export function isNativeApp() {
  return Capacitor.isNativePlatform();
}

// Function to take a photo using the device's camera
export async function takePhoto() {
  // If not in native environment, use web camera
  if (!isNativeApp()) {
    console.log('Not in native environment, using web camera');
    return null;
  }
  
  try {
    const image = await Camera.getPhoto({
      quality: 90,
      allowEditing: false,
      resultType: 'uri',
      source: 'CAMERA'
    });
    
    // Return the image URI that can be used in an img tag
    return image.webPath;
  } catch (error) {
    console.error('Error taking photo:', error);
    return null;
  }
}

// Function to request camera permissions
export async function requestCameraPermissions() {
  if (!isNativeApp()) {
    return true;
  }
  
  try {
    const permissions = await Camera.requestPermissions();
    return permissions.camera === 'granted';
  } catch (error) {
    console.error('Error requesting camera permissions:', error);
    return false;
  }
}

// Initialize when the script loads
document.addEventListener('DOMContentLoaded', () => {
  if (isNativeApp()) {
    console.log('Running in Capacitor native environment');
    // Request camera permissions early
    requestCameraPermissions();
  } else {
    console.log('Running in web environment');
  }
});