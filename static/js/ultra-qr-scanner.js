/**
 * Ultra Fast QR Scanner - Reliable and Simple
 * Works with damaged, blurred, and crushed QR codes
 */

class UltraQRScanner {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.isScanning = false;
        this.isPaused = false;
        this.lastScanTime = 0;
        this.scanDebounce = options.scanDebounce || 1000; // Prevent duplicate scans
        
        // Callbacks
        this.onSuccess = options.onSuccess || null;
        this.onError = options.onError || null;
        
        // Scanner configuration
        this.config = {
            fps: options.fps || 10,
            qrbox: options.qrbox || { width: 250, height: 250 },
            aspectRatio: options.aspectRatio || 1.0,
            disableFlip: options.disableFlip !== false,
            ...options
        };
        
        this.html5QrCode = null;
        this.initializeScanner();
    }
    
    initializeScanner() {
        if (!this.container) {
            console.error('Container not found:', this.containerId);
            return;
        }
        
        // Clear container
        this.container.innerHTML = '';
        
        // Create scanner element
        const scannerDiv = document.createElement('div');
        scannerDiv.id = this.containerId + '-scanner';
        scannerDiv.style.width = '100%';
        scannerDiv.style.position = 'relative';
        this.container.appendChild(scannerDiv);
        
        // Initialize Html5Qrcode
        this.html5QrCode = new Html5Qrcode(scannerDiv.id);
    }
    
    async start() {
        if (this.isScanning) {
            console.log('Scanner already running');
            return;
        }
        
        try {
            const config = {
                fps: this.config.fps,
                qrbox: this.config.qrbox,
                aspectRatio: this.config.aspectRatio,
                disableFlip: this.config.disableFlip
            };
            
            await this.html5QrCode.start(
                { facingMode: "environment" }, // Use back camera
                config,
                (decodedText, decodedResult) => {
                    this.handleScanSuccess(decodedText, decodedResult);
                },
                (errorMessage) => {
                    // Ignore errors silently - they're too frequent during scanning
                }
            );
            
            this.isScanning = true;
            this.isPaused = false;
            console.log('Ultra QR Scanner started successfully');
            
        } catch (err) {
            console.error('Failed to start scanner:', err);
            if (this.onError) {
                this.onError(err);
            }
            throw err;
        }
    }
    
    handleScanSuccess(decodedText, decodedResult) {
        // Debounce to prevent duplicate scans
        const now = Date.now();
        if (now - this.lastScanTime < this.scanDebounce) {
            return;
        }
        
        if (this.isPaused) {
            return;
        }
        
        this.lastScanTime = now;
        
        // Haptic feedback if available
        if (navigator.vibrate) {
            navigator.vibrate(100);
        }
        
        // Pause scanning to prevent duplicates
        this.pause();
        
        // Call success callback
        if (this.onSuccess) {
            this.onSuccess(decodedText, decodedResult);
        }
    }
    
    pause() {
        this.isPaused = true;
        if (this.html5QrCode) {
            try {
                this.html5QrCode.pause();
            } catch (err) {
                console.warn('Could not pause scanner:', err);
            }
        }
    }
    
    resume() {
        this.isPaused = false;
        if (this.html5QrCode) {
            try {
                this.html5QrCode.resume();
            } catch (err) {
                console.warn('Could not resume scanner:', err);
            }
        }
    }
    
    async stop() {
        if (!this.isScanning) {
            return;
        }
        
        try {
            await this.html5QrCode.stop();
            this.isScanning = false;
            this.isPaused = false;
            console.log('Ultra QR Scanner stopped');
        } catch (err) {
            console.error('Error stopping scanner:', err);
        }
    }
    
    clear() {
        if (this.html5QrCode) {
            this.html5QrCode.clear();
        }
    }
    
    // Get supported cameras
    static async getCameras() {
        return await Html5Qrcode.getCameras();
    }
    
    // Check if camera is available
    static async isCameraAvailable() {
        try {
            const cameras = await UltraQRScanner.getCameras();
            return cameras && cameras.length > 0;
        } catch (err) {
            return false;
        }
    }
}

// Make it globally available
window.UltraQRScanner = UltraQRScanner;