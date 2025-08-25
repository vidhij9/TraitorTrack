/**
 * Camera Permission Management System
 * ==================================
 * 
 * This module handles persistent camera permissions for mobile devices,
 * ensuring users are not repeatedly prompted for camera access once granted.
 */

class CameraPermissionManager {
    constructor() {
        this.storageKey = 'tracetrack_camera_permission';
        this.permissionGranted = this.getStoredPermission();
        this.checkInterval = null;
    }

    /**
     * Check if camera permission has been previously granted
     */
    getStoredPermission() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            return stored === 'granted';
        } catch (e) {
            console.warn('LocalStorage not available, using session-based permission tracking');
            return false;
        }
    }

    /**
     * Store camera permission status
     */
    storePermission(granted) {
        try {
            localStorage.setItem(this.storageKey, granted ? 'granted' : 'denied');
            this.permissionGranted = granted;
        } catch (e) {
            console.warn('Cannot store permission in localStorage');
            this.permissionGranted = granted;
        }
    }

    /**
     * Check current browser permission status using Permissions API
     */
    async checkBrowserPermission() {
        if (!navigator.permissions || !navigator.permissions.query) {
            console.log('Permissions API not supported');
            return null;
        }

        try {
            const result = await navigator.permissions.query({ name: 'camera' });
            console.log('Browser camera permission:', result.state);
            
            // Update stored permission based on browser state
            if (result.state === 'granted') {
                this.storePermission(true);
                return 'granted';
            } else if (result.state === 'denied') {
                this.storePermission(false);
                return 'denied';
            }
            
            return result.state; // 'prompt' or other states
        } catch (error) {
            console.warn('Error checking camera permission:', error);
            return null;
        }
    }

    /**
     * Request camera access with intelligent permission handling
     */
    async requestCameraAccess(constraints = null) {
        console.log('Requesting camera access...');
        
        // Default constraints optimized for QR scanning
        const defaultConstraints = {
            video: {
                facingMode: 'environment',
                width: { ideal: 1920, min: 640 },
                height: { ideal: 1080, min: 480 },
                frameRate: { ideal: 30, min: 15 }
            }
        };

        const finalConstraints = constraints || defaultConstraints;

        try {
            // Check browser permission first
            const browserPermission = await this.checkBrowserPermission();
            
            // If we know permission is denied, show helpful message
            if (browserPermission === 'denied') {
                throw new Error('PERMISSION_DENIED');
            }

            // If we have stored permission or browser shows granted, try to access directly
            if (this.permissionGranted || browserPermission === 'granted') {
                console.log('Using stored/browser permission, accessing camera...');
            } else {
                console.log('First-time access or permission unknown, requesting...');
            }

            // Request camera access
            const stream = await navigator.mediaDevices.getUserMedia(finalConstraints);
            
            // Success! Store the permission
            this.storePermission(true);
            console.log('Camera access granted and stored');
            
            return stream;

        } catch (error) {
            console.error('Camera access failed:', error);
            
            if (error.name === 'NotAllowedError' || error.message === 'PERMISSION_DENIED') {
                // User denied permission
                this.storePermission(false);
                throw new Error('PERMISSION_DENIED');
            } else if (error.name === 'NotFoundError') {
                throw new Error('NO_CAMERA');
            } else if (error.name === 'OverconstrainedError') {
                // Try with basic constraints
                console.log('Retrying with basic constraints...');
                try {
                    const basicStream = await navigator.mediaDevices.getUserMedia({ video: true });
                    this.storePermission(true);
                    return basicStream;
                } catch (basicError) {
                    throw basicError;
                }
            } else {
                throw error;
            }
        }
    }

    /**
     * Start monitoring permission changes (for when user changes permission in browser settings)
     */
    startPermissionMonitoring() {
        if (!navigator.permissions || !navigator.permissions.query) {
            return;
        }

        // Clear any existing monitoring
        this.stopPermissionMonitoring();

        // Monitor permission changes
        this.checkInterval = setInterval(async () => {
            try {
                const result = await navigator.permissions.query({ name: 'camera' });
                const currentStored = this.getStoredPermission();
                
                // Update if permission changed in browser settings
                if (result.state === 'granted' && !currentStored) {
                    console.log('Camera permission granted in browser settings');
                    this.storePermission(true);
                } else if (result.state === 'denied' && currentStored) {
                    console.log('Camera permission revoked in browser settings');
                    this.storePermission(false);
                }
            } catch (error) {
                // Ignore errors in monitoring
            }
        }, 5000); // Check every 5 seconds
    }

    /**
     * Stop permission monitoring
     */
    stopPermissionMonitoring() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }

    /**
     * Reset stored permissions (for testing or user request)
     */
    resetPermissions() {
        try {
            localStorage.removeItem(this.storageKey);
            this.permissionGranted = false;
            console.log('Camera permissions reset');
        } catch (e) {
            this.permissionGranted = false;
        }
    }

    /**
     * Get user-friendly error message based on error type
     */
    getErrorMessage(error) {
        switch (error.message || error.name) {
            case 'PERMISSION_DENIED':
            case 'NotAllowedError':
                return 'Camera access was denied. To enable camera scanning, please allow camera permissions in your browser settings and refresh the page.';
            
            case 'NO_CAMERA':
            case 'NotFoundError':
                return 'No camera found on this device. Please ensure your device has a camera and try again.';
            
            case 'OverconstrainedError':
                return 'Camera settings are not supported on this device. The app will try to use basic camera settings instead.';
            
            default:
                return 'Camera initialization failed. Please check your device and browser settings, then refresh the page.';
        }
    }

    /**
     * Show permission instructions for mobile users
     */
    showMobileInstructions() {
        const userAgent = navigator.userAgent.toLowerCase();
        let instructions = '';

        if (userAgent.includes('safari') && userAgent.includes('mobile')) {
            // iOS Safari
            instructions = 'On iOS: Go to Settings > Safari > Camera, then allow camera access. Refresh this page after changing settings.';
        } else if (userAgent.includes('chrome') && userAgent.includes('mobile')) {
            // Mobile Chrome
            instructions = 'On mobile Chrome: Tap the camera icon in the address bar, or go to site settings and allow camera access.';
        } else if (userAgent.includes('firefox') && userAgent.includes('mobile')) {
            // Mobile Firefox
            instructions = 'On mobile Firefox: Tap the shield icon and allow camera permissions for this site.';
        } else {
            // Generic instructions
            instructions = 'Please allow camera access in your browser settings and refresh the page.';
        }

        return instructions;
    }
}

// Global instance
window.CameraPermissionManager = window.CameraPermissionManager || CameraPermissionManager;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CameraPermissionManager;
}