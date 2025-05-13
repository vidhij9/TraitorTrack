/**
 * Native integration for TraceTrack mobile app
 * This script enhances the web app with native capabilities when running in Capacitor
 */

// Function to check if we're running in Capacitor
function isNativeApp() {
  return typeof window.Capacitor !== 'undefined' && window.Capacitor.isNativePlatform();
}

// Function to initialize native enhancements
function initNativeFeatures() {
  if (!isNativeApp()) {
    console.log('Running in browser mode - native features disabled');
    return;
  }
  
  console.log('Initializing native app features');
  
  // Add the native app class to the body for CSS styling
  document.body.classList.add('native-app');
  
  // Integrate with QR scanner pages if they exist
  enhanceQRScanning();
  
  // Add hardware back button support
  addBackButtonSupport();
  
  // Add native status bar styling
  styleStatusBar();
}

// Function to enhance QR scanning with native camera
function enhanceQRScanning() {
  // Find QR reader elements
  const qrScannerDiv = document.getElementById('qr-reader');
  
  if (!qrScannerDiv) {
    console.log('No QR scanner found on page');
    return;
  }
  
  console.log('Native camera integration for QR scanning enabled');
  
  // Create a button to use native camera
  const nativeCameraButton = document.createElement('button');
  nativeCameraButton.className = 'btn btn-primary mt-2 mb-3 native-camera-btn';
  nativeCameraButton.innerHTML = '<i class="fas fa-camera"></i> Use Native Camera';
  nativeCameraButton.addEventListener('click', useNativeCamera);
  
  // Insert the button before the QR reader
  qrScannerDiv.parentNode.insertBefore(nativeCameraButton, qrScannerDiv);
  
  // Add a note about improved scanning
  const nativeNote = document.createElement('p');
  nativeNote.className = 'text-muted small native-camera-note';
  nativeNote.innerHTML = 'Native camera provides better QR scanning performance';
  qrScannerDiv.parentNode.insertBefore(nativeNote, qrScannerDiv.nextSibling);
}

// Function to use the native camera for QR scanning
async function useNativeCamera() {
  const { Camera } = window.Capacitor.Plugins;
  
  try {
    // Request camera permissions
    const permissionStatus = await Camera.requestPermissions();
    
    if (permissionStatus.camera !== 'granted') {
      alert('Camera permission is required to scan QR codes');
      return;
    }
    
    // Use the Capacitor Camera API
    const image = await Camera.getPhoto({
      quality: 90,
      allowEditing: false,
      resultType: 'base64',
      source: 'CAMERA'
    });
    
    // Once we have the image, we need to process it with a QR decoder
    // This would typically be done with a library like jsQR
    alert('Image captured! Scan functionality in development.');
    
    // For now, we'll just log that we captured an image
    console.log('Image captured in base64 format');
    
  } catch (error) {
    console.error('Error using native camera:', error);
    alert('Failed to open camera. Please check permissions and try again.');
  }
}

// Function to handle hardware back button
function addBackButtonSupport() {
  const { App } = window.Capacitor.Plugins;
  
  App.addListener('backButton', ({ canGoBack }) => {
    if (canGoBack) {
      window.history.back();
    } else {
      // Ask to exit the app if we can't go back
      if (confirm('Do you want to exit the app?')) {
        App.exitApp();
      }
    }
  });
}

// Function to style the status bar
function styleStatusBar() {
  const { StatusBar } = window.Capacitor.Plugins;
  
  if (StatusBar) {
    // Set status bar color to match our theme
    StatusBar.setBackgroundColor({ color: '#4CAF50' });
    StatusBar.setStyle({ style: 'DARK' });
  }
}

// Initialize when the DOM is ready
document.addEventListener('DOMContentLoaded', initNativeFeatures);