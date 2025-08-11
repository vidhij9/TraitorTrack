/**
 * Instant QR Scanner - Immediate camera access
 * Simplified approach for maximum reliability
 */

class InstantQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.scanner = null;
        this.isScanning = false;
        this.onSuccess = null;
        
        console.log('InstantQR: Starting immediate camera access');
        this.setup();
    }
    
    setup() {
        // Clear container and add simple interface
        this.container.innerHTML = `
            <div class="instant-scanner">
                <div id="${this.containerId}-reader" class="scanner-area"></div>
                <div class="scanner-status" id="scanner-status">
                    <div class="status-text">Instant Scanner</div>
                    <div class="status-indicator">Starting camera...</div>
                </div>
            </div>
            
            <style>
                .instant-scanner {
                    position: relative;
                    width: 100%;
                    min-height: 400px;
                    background: #000;
                    border-radius: 8px;
                    overflow: hidden;
                }
                
                .scanner-area {
                    width: 100%;
                    height: 400px;
                }
                
                .scanner-status {
                    position: absolute;
                    bottom: 20px;
                    left: 20px;
                    right: 20px;
                    background: rgba(0,0,0,0.8);
                    color: white;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                }
                
                .status-text {
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                
                .status-indicator {
                    font-size: 14px;
                    opacity: 0.8;
                }
                
                .scanner-success {
                    background: rgba(0,255,0,0.9) !important;
                    color: black !important;
                }
                
                .scanner-error {
                    background: rgba(255,0,0,0.9) !important;
                }
            </style>
        `;
        
        // Start immediately
        this.startCamera();
    }
    
    updateStatus(text, isSuccess = false, isError = false) {
        const statusEl = document.getElementById('scanner-status');
        const indicatorEl = statusEl?.querySelector('.status-indicator');
        
        if (indicatorEl) {
            indicatorEl.textContent = text;
        }
        
        if (statusEl) {
            statusEl.className = 'scanner-status' + 
                (isSuccess ? ' scanner-success' : '') +
                (isError ? ' scanner-error' : '');
        }
    }
    
    async startCamera() {
        try {
            console.log('InstantQR: Initializing Html5Qrcode...');
            
            // Wait for library
            if (typeof Html5Qrcode === 'undefined') {
                this.updateStatus('Loading QR library...', false, false);
                await this.waitForLibrary();
            }
            
            this.updateStatus('Accessing camera...', false, false);
            
            // Create scanner
            this.scanner = new Html5Qrcode(`${this.containerId}-reader`);
            
            // Get cameras
            const cameras = await Html5Qrcode.getCameras();
            console.log('InstantQR: Found cameras:', cameras.length);
            
            if (cameras.length === 0) {
                throw new Error('No cameras found');
            }
            
            // Use first available camera with minimal config
            const config = {
                fps: 15,
                qrbox: 200
            };
            
            this.updateStatus('Starting camera feed...', false, false);
            
            await this.scanner.start(
                cameras[0].id,
                config,
                (decodedText, decodedResult) => {
                    console.log('InstantQR: QR detected:', decodedText);
                    this.handleSuccess(decodedText, decodedResult);
                },
                (errorMessage) => {
                    // Ignore scan errors
                }
            );
            
            this.isScanning = true;
            this.updateStatus('Camera active - Ready to scan!', true, false);
            console.log('InstantQR: Scanner started successfully');
            
        } catch (error) {
            console.error('InstantQR: Failed to start:', error);
            this.updateStatus(`Camera error: ${error.message}`, false, true);
            
            // Try fallback
            setTimeout(() => {
                this.tryFallback();
            }, 2000);
        }
    }
    
    async waitForLibrary() {
        return new Promise((resolve) => {
            const check = () => {
                if (typeof Html5Qrcode !== 'undefined') {
                    resolve();
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    }
    
    handleSuccess(decodedText, decodedResult) {
        this.updateStatus(`QR Code: ${decodedText}`, true, false);
        
        if (this.onSuccess) {
            this.onSuccess(decodedText, decodedResult);
        }
        
        // Reset status after 3 seconds
        setTimeout(() => {
            if (this.isScanning) {
                this.updateStatus('Ready for next scan', true, false);
            }
        }, 3000);
    }
    
    async tryFallback() {
        try {
            this.updateStatus('Trying fallback approach...', false, false);
            
            // Simplest possible configuration
            this.scanner = new Html5Qrcode(`${this.containerId}-reader`);
            
            await this.scanner.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: 150 },
                (text) => this.handleSuccess(text),
                () => {}
            );
            
            this.isScanning = true;
            this.updateStatus('Fallback scanner active', true, false);
            
        } catch (error) {
            console.error('InstantQR: Fallback failed:', error);
            this.updateStatus('Camera unavailable - Check permissions', false, true);
        }
    }
    
    async stop() {
        if (this.scanner && this.isScanning) {
            try {
                await this.scanner.stop();
                this.isScanning = false;
                this.updateStatus('Scanner stopped', false, false);
            } catch (error) {
                console.error('InstantQR: Stop error:', error);
            }
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
        console.log('InstantQR: Success callback set');
    }
}

// Export
window.InstantQRScanner = InstantQRScanner;
console.log('InstantQRScanner loaded');