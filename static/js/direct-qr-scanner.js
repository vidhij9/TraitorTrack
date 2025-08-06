/**
 * Direct QR Scanner - No frills, just works
 * Bypasses all complex initialization for immediate camera access
 */

class DirectQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.scanner = null;
        this.isScanning = false;
        this.onSuccess = null;
        
        console.log('DirectQRScanner: Constructor called for', containerId);
        this.init();
    }
    
    init() {
        console.log('DirectQRScanner: Initializing...');
        
        // Clear container
        this.container.innerHTML = `
            <div class="direct-scanner">
                <div id="${this.containerId}-qr-reader" style="width: 100%; height: 400px; background: #000; border-radius: 8px;"></div>
                <div class="scanner-message" id="scanner-message" style="text-align: center; padding: 20px; color: #333;">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div style="margin-top: 10px;">Initializing camera...</div>
                </div>
            </div>
        `;
        
        // Start immediately
        setTimeout(() => {
            this.startScanning();
        }, 500);
    }
    
    updateMessage(message, type = 'info') {
        const messageEl = document.getElementById('scanner-message');
        if (messageEl) {
            const colors = {
                success: 'text-success',
                error: 'text-danger',
                info: 'text-primary'
            };
            
            messageEl.innerHTML = `<div class="${colors[type] || 'text-info'}">${message}</div>`;
        }
    }
    
    async startScanning() {
        console.log('DirectQRScanner: Starting camera...');
        
        try {
            // Check if Html5Qrcode is available
            if (typeof Html5Qrcode === 'undefined') {
                console.error('Html5Qrcode not loaded');
                this.updateMessage('QR scanner library not loaded', 'error');
                return;
            }
            
            this.updateMessage('Getting camera access...', 'info');
            
            // Create scanner instance
            this.scanner = new Html5Qrcode(`${this.containerId}-qr-reader`);
            console.log('DirectQRScanner: Html5Qrcode instance created');
            
            // Get cameras with error handling
            let cameras;
            try {
                cameras = await Html5Qrcode.getCameras();
                console.log('DirectQRScanner: Found cameras:', cameras.length);
            } catch (err) {
                console.error('DirectQRScanner: Failed to get cameras:', err);
                this.updateMessage('Camera access denied or unavailable', 'error');
                return;
            }
            
            if (!cameras || cameras.length === 0) {
                console.error('DirectQRScanner: No cameras found');
                this.updateMessage('No cameras found on this device', 'error');
                return;
            }
            
            // Use first available camera (simplest approach)
            const cameraId = cameras[0].id;
            console.log('DirectQRScanner: Using camera:', cameras[0].label || cameraId);
            
            this.updateMessage('Starting camera...', 'info');
            
            // Minimal config for maximum compatibility
            const config = {
                fps: 10,
                qrbox: 200,
                aspectRatio: 1.0
            };
            
            // Start scanning
            await this.scanner.start(
                cameraId,
                config,
                (decodedText, decodedResult) => {
                    console.log('DirectQRScanner: QR detected:', decodedText);
                    this.updateMessage('QR Code detected!', 'success');
                    
                    if (this.onSuccess) {
                        this.onSuccess(decodedText, decodedResult);
                    }
                },
                (errorMessage) => {
                    // Silent - scan errors are normal
                }
            );
            
            this.isScanning = true;
            this.updateMessage('Camera ready - Scan QR codes', 'success');
            console.log('DirectQRScanner: Started successfully');
            
        } catch (error) {
            console.error('DirectQRScanner: Start error:', error);
            this.updateMessage(`Camera failed: ${error.message}`, 'error');
        }
    }
    
    async stop() {
        if (this.scanner && this.isScanning) {
            try {
                await this.scanner.stop();
                this.isScanning = false;
                this.updateMessage('Camera stopped', 'info');
                console.log('DirectQRScanner: Stopped');
            } catch (error) {
                console.error('DirectQRScanner: Stop error:', error);
            }
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
        console.log('DirectQRScanner: Success callback set');
    }
}

// Make globally available
window.DirectQRScanner = DirectQRScanner;
console.log('DirectQRScanner loaded and ready');