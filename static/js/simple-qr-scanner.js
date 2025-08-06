/**
 * Simple QR Scanner - Reliable and Fast
 * Focused on getting camera working immediately
 */

class SimpleQRScanner {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.options = {
            fps: 30,
            qrbox: { width: 300, height: 300 },
            ...options
        };
        
        this.html5QrCode = null;
        this.isScanning = false;
        this.onSuccess = null;
        
        this.setupContainer();
    }
    
    setupContainer() {
        this.container.innerHTML = `
            <div class="qr-scanner-container">
                <div id="${this.containerId}-reader" style="width: 100%; min-height: 300px;"></div>
            </div>
        `;
    }
    
    async start() {
        if (this.isScanning) return;
        
        try {
            console.log('Initializing HTML5-QRCode scanner...');
            this.html5QrCode = new Html5Qrcode(`${this.containerId}-reader`);
            
            // Get cameras
            const cameras = await Html5Qrcode.getCameras();
            console.log('Available cameras:', cameras.length);
            
            if (cameras.length === 0) {
                throw new Error('No cameras found');
            }
            
            // Use rear camera if available
            const rearCamera = cameras.find(camera => 
                camera.label.toLowerCase().includes('back') || 
                camera.label.toLowerCase().includes('rear') ||
                camera.label.toLowerCase().includes('environment')
            ) || cameras[0];
            
            console.log('Using camera:', rearCamera.label);
            
            // Simple config that works reliably
            const config = {
                fps: this.options.fps,
                qrbox: this.options.qrbox,
                aspectRatio: 1.0
            };
            
            await this.html5QrCode.start(
                rearCamera.id,
                config,
                (decodedText, decodedResult) => {
                    console.log('QR Code detected:', decodedText);
                    if (this.onSuccess) {
                        this.onSuccess(decodedText, decodedResult);
                    }
                },
                (errorMessage) => {
                    // Ignore scan errors - they're too frequent
                }
            );
            
            this.isScanning = true;
            console.log('Scanner started successfully');
            
        } catch (error) {
            console.error('Scanner start error:', error);
            throw error;
        }
    }
    
    async stop() {
        if (!this.isScanning || !this.html5QrCode) return;
        
        try {
            await this.html5QrCode.stop();
            this.isScanning = false;
            console.log('Scanner stopped');
        } catch (error) {
            console.error('Scanner stop error:', error);
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
}

// Make it globally available
window.SimpleQRScanner = SimpleQRScanner;