/**
 * Camera Permission Helper - Robust permission handling for TraceTrack scanners
 */

class CameraPermissionHelper {
    constructor() {
        this.permissionKey = 'tracetrack_camera_permission';
        this.hasAskedPermission = false;
    }

    // Check if camera is supported
    isCameraSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    // Get stored permission state
    getStoredPermission() {
        return localStorage.getItem(this.permissionKey);
    }

    // Store permission state
    storePermission(state) {
        localStorage.setItem(this.permissionKey, state);
    }

    // Check browser permission status
    async checkPermissionStatus() {
        try {
            if (navigator.permissions) {
                const permission = await navigator.permissions.query({ name: 'camera' });
                return permission.state; // 'granted', 'denied', or 'prompt'
            }
        } catch (e) {
            console.log('Permission API not available');
        }
        return 'unknown';
    }

    // Request camera access with multiple fallback levels
    async requestCameraAccess() {
        if (!this.isCameraSupported()) {
            throw new Error('Camera not supported by this browser. Please use Chrome, Firefox, or Safari.');
        }

        // Check browser permission first
        const permissionStatus = await this.checkPermissionStatus();
        console.log('Camera permission status:', permissionStatus);

        if (permissionStatus === 'denied') {
            throw new Error('Camera access was denied. Please click the camera icon in your browser address bar and allow access, then refresh the page.');
        }

        // Try progressive constraint levels
        const constraintLevels = [
            // Level 1: Mobile-optimized
            {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 640, max: 1280 },
                    height: { ideal: 480, max: 720 },
                    frameRate: { ideal: 30, max: 60 }
                },
                audio: false
            },
            // Level 2: Basic rear camera
            {
                video: { facingMode: 'environment' },
                audio: false
            },
            // Level 3: Any camera
            {
                video: true,
                audio: false
            }
        ];

        let lastError = null;
        let stream = null;

        for (let i = 0; i < constraintLevels.length; i++) {
            try {
                console.log(`Trying camera constraint level ${i + 1}...`);
                stream = await navigator.mediaDevices.getUserMedia(constraintLevels[i]);
                console.log(`Camera access successful with level ${i + 1}`);
                
                // Store success
                this.storePermission('granted');
                this.hasAskedPermission = true;
                
                return stream;
                
            } catch (error) {
                console.log(`Constraint level ${i + 1} failed:`, error.name, error.message);
                lastError = error;

                // Handle specific error types
                if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
                    this.storePermission('denied');
                    throw new Error('Camera permission denied. Please allow camera access in your browser settings and refresh the page.');
                }

                if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
                    // No point trying other constraints if no camera exists
                    throw new Error('No camera found. Please connect a camera and try again.');
                }

                if (error.name === 'NotReadableError') {
                    throw new Error('Camera is already in use by another application. Please close other camera apps and try again.');
                }

                // Continue to next level for other errors
                continue;
            }
        }

        // If we reach here, all levels failed
        if (lastError) {
            throw new Error(`Camera initialization failed: ${lastError.message}`);
        } else {
            throw new Error('Failed to access camera with all constraint levels.');
        }
    }

    // Show user-friendly permission guide
    showPermissionGuide() {
        return {
            title: 'Camera Access Required',
            message: 'To scan QR codes, please allow camera access:',
            steps: [
                '1. Click the camera icon in your browser address bar',
                '2. Select "Allow" for camera access',
                '3. Refresh the page and try scanning again'
            ],
            browsers: {
                chrome: 'Look for the camera icon next to the address bar',
                firefox: 'Click the shield icon and allow camera',
                safari: 'Go to Safari > Settings > Websites > Camera'
            }
        };
    }

    // Reset permission state (for debugging)
    resetPermissions() {
        localStorage.removeItem(this.permissionKey);
        this.hasAskedPermission = false;
        console.log('Camera permissions reset');
    }
}

// Global instance
window.CameraPermissionHelper = CameraPermissionHelper;
window.cameraPermissionHelper = new CameraPermissionHelper();