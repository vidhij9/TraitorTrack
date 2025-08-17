/**
 * Enhanced Camera Access Handler for Agricultural QR Scanning
 * Fixes common camera issues on mobile devices and production environments
 */
class CameraFixManager {
    constructor() {
        this.permissionGranted = localStorage.getItem('camera_permission') === 'granted';
        this.constraints = this.getOptimalConstraints();
        this.fallbackConstraints = this.getFallbackConstraints();
        this.initializeDebugMode();
    }

    initializeDebugMode() {
        // Enable detailed logging for camera debugging
        this.debug = window.location.search.includes('debug=camera');
        if (this.debug) {
            console.log('🔧 Camera Debug Mode Enabled');
            this.logCameraCapabilities();
        }
    }

    async logCameraCapabilities() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(device => device.kind === 'videoinput');
            console.log('📹 Available cameras:', videoDevices.length);
            videoDevices.forEach((device, index) => {
                console.log(`Camera ${index + 1}:`, device.label || 'Unknown Camera');
            });

            // Check supported constraints
            const supportedConstraints = navigator.mediaDevices.getSupportedConstraints();
            console.log('🎯 Supported constraints:', supportedConstraints);
        } catch (error) {
            console.warn('Could not enumerate devices:', error);
        }
    }

    getOptimalConstraints() {
        return {
            video: {
                facingMode: { ideal: 'environment' },
                width: { ideal: 800, min: 320, max: 1920 },
                height: { ideal: 600, min: 240, max: 1080 },
                frameRate: { ideal: 30, min: 15, max: 60 },
                // Advanced constraints for better QR detection
                aspectRatio: { ideal: 4/3 },
                focusMode: { ideal: 'continuous' },
                whiteBalanceMode: { ideal: 'continuous' },
                exposureMode: { ideal: 'continuous' }
            },
            audio: false
        };
    }

    getFallbackConstraints() {
        return [
            // Ultra-basic constraints for maximum compatibility
            { video: true, audio: false },
            // Basic rear camera
            { video: { facingMode: 'environment' }, audio: false },
            // Front camera fallback
            { video: { facingMode: 'user' }, audio: false },
            // Minimal constraints
            { video: { width: 320, height: 240 }, audio: false }
        ];
    }

    async requestCameraAccess() {
        console.log('🎥 Attempting camera access...');

        // Check if camera is available
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            throw new Error('Camera not supported in this browser');
        }

        // Check HTTPS requirement
        if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
            console.warn('⚠️ Camera requires HTTPS in production');
        }

        try {
            // Try optimal constraints first
            console.log('📱 Trying optimal constraints...');
            const stream = await navigator.mediaDevices.getUserMedia(this.constraints);
            
            localStorage.setItem('camera_permission', 'granted');
            console.log('✅ Camera access granted with optimal settings');
            
            return stream;

        } catch (error) {
            console.warn('❌ Optimal constraints failed:', error.message);
            
            // Try fallback constraints one by one
            for (let i = 0; i < this.fallbackConstraints.length; i++) {
                const constraints = this.fallbackConstraints[i];
                console.log(`🔄 Trying fallback ${i + 1}:`, constraints);
                
                try {
                    const stream = await navigator.mediaDevices.getUserMedia(constraints);
                    localStorage.setItem('camera_permission', 'granted');
                    console.log(`✅ Camera access granted with fallback ${i + 1}`);
                    
                    return stream;
                    
                } catch (fallbackError) {
                    console.warn(`❌ Fallback ${i + 1} failed:`, fallbackError.message);
                    continue;
                }
            }

            // All attempts failed
            this.handleCameraError(error);
            throw error;
        }
    }

    handleCameraError(error) {
        console.error('🚨 All camera access attempts failed:', error);
        
        let userMessage = 'Camera access failed. ';
        let troubleshootingSteps = [];

        switch (error.name) {
            case 'NotAllowedError':
                userMessage += 'Camera permission was denied.';
                troubleshootingSteps = [
                    '1. Click the camera/lock icon in your browser address bar',
                    '2. Allow camera access for this website',
                    '3. Refresh the page and try again',
                    '4. On mobile: Check browser permissions in device settings'
                ];
                break;
                
            case 'NotFoundError':
                userMessage += 'No camera was found on this device.';
                troubleshootingSteps = [
                    '1. Make sure your device has a camera',
                    '2. Check if camera is being used by another app',
                    '3. Try using a different device or browser'
                ];
                break;
                
            case 'OverconstrainedError':
                userMessage += 'Camera constraints not supported.';
                troubleshootingSteps = [
                    '1. Your camera may not support the required settings',
                    '2. Try using a different browser (Chrome/Safari recommended)',
                    '3. Update your browser to the latest version'
                ];
                break;
                
            case 'NotReadableError':
                userMessage += 'Camera is busy or not accessible.';
                troubleshootingSteps = [
                    '1. Close other apps that might be using the camera',
                    '2. Restart your browser',
                    '3. On mobile: Close camera/video apps and try again'
                ];
                break;
                
            default:
                userMessage += `Camera error: ${error.message}`;
                troubleshootingSteps = [
                    '1. Make sure you\'re using HTTPS (required for camera)',
                    '2. Try using Chrome or Safari browser',
                    '3. Check if camera permissions are enabled',
                    '4. Refresh the page and try again'
                ];
        }

        this.showCameraErrorUI(userMessage, troubleshootingSteps);
    }

    showCameraErrorUI(message, steps) {
        // Create error modal
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        `;

        const content = document.createElement('div');
        content.style.cssText = `
            background: white;
            padding: 30px;
            border-radius: 15px;
            max-width: 500px;
            width: 100%;
            max-height: 80vh;
            overflow-y: auto;
        `;

        content.innerHTML = `
            <h3 style="color: #dc3545; margin-top: 0;">📱 Camera Access Issue</h3>
            <p style="margin-bottom: 20px;">${message}</p>
            <h4>Troubleshooting Steps:</h4>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                ${steps.map(step => `<p style="margin: 8px 0;">${step}</p>`).join('')}
            </div>
            <div style="text-align: center; margin-top: 20px;">
                <button onclick="this.closest('.camera-error-modal').remove(); location.reload();" 
                        style="background: #007bff; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; margin: 5px;">
                    Try Again
                </button>
                <button onclick="this.closest('.camera-error-modal').remove();" 
                        style="background: #6c757d; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; margin: 5px;">
                    Close
                </button>
            </div>
            <div style="margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 8px; font-size: 14px;">
                <strong>💡 Pro Tip:</strong> For best results scanning agricultural bags:
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>Use Chrome or Safari browser</li>
                    <li>Ensure good lighting on QR codes</li>
                    <li>Hold device steady when scanning</li>
                    <li>Clean camera lens if needed</li>
                </ul>
            </div>
        `;

        modal.className = 'camera-error-modal';
        modal.appendChild(content);
        document.body.appendChild(modal);
    }

    async testCameraAccess() {
        try {
            const stream = await this.requestCameraAccess();
            console.log('✅ Camera test successful');
            
            // Stop the test stream
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
            
            return true;
        } catch (error) {
            console.error('❌ Camera test failed:', error);
            return false;
        }
    }

    // Enhanced camera setup for HTML5-QRCode library
    async setupHtml5QrCode(html5QrCode) {
        try {
            const devices = await Html5Qrcode.getCameras();
            if (devices && devices.length > 0) {
                // Prefer back camera for QR scanning
                const backCamera = devices.find(device => 
                    device.label.toLowerCase().includes('back') ||
                    device.label.toLowerCase().includes('rear') ||
                    device.label.toLowerCase().includes('environment')
                ) || devices[devices.length - 1]; // Fallback to last device

                console.log(`🎯 Using camera: ${backCamera.label || 'Unknown'}`);

                // Start with agricultural-optimized settings
                const config = {
                    fps: 30,
                    qrbox: { width: 250, height: 250 },
                    aspectRatio: 1.0,
                    disableFlip: false,
                    experimentalFeatures: {
                        useBarCodeDetectorIfSupported: true
                    }
                };

                await html5QrCode.start(backCamera.id, config, 
                    (decodedText) => {
                        console.log('🌾 Agricultural QR detected:', decodedText);
                        // Handle successful scan
                        if (window.onQRScanSuccess) {
                            window.onQRScanSuccess(decodedText);
                        }
                    },
                    (error) => {
                        // Ignore frequent scan errors
                        if (this.debug && error !== 'QR code parse error, error = NotFoundException: No MultiFormat Readers were able to detect the code.') {
                            console.log('Scan error:', error);
                        }
                    }
                );

                return true;
            } else {
                throw new Error('No cameras found');
            }
        } catch (error) {
            console.error('HTML5-QRCode setup failed:', error);
            throw error;
        }
    }
}

// Global camera manager instance
window.cameraFixManager = new CameraFixManager();

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎬 Camera Fix Manager initialized for agricultural QR scanning');
    
    // Test camera access immediately for debugging
    if (window.location.search.includes('test=camera')) {
        setTimeout(() => {
            window.cameraFixManager.testCameraAccess();
        }, 1000);
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CameraFixManager;
}