/**
 * Basic QR Scanner - Maximum Compatibility
 * Designed to work immediately without complex setup
 */

class BasicQRScanner {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.isScanning = false;
        this.onSuccess = null;
        this.scanner = null;
        
        console.log('BasicQRScanner constructor called for:', containerId);
        this.setupContainer();
    }
    
    setupContainer() {
        console.log('Setting up scanner container...');
        this.container.innerHTML = `
            <div class="basic-qr-scanner">
                <div id="${this.containerId}-reader" class="qr-reader-container"></div>
                <div class="scanner-status" id="scanner-status">
                    <div class="status-indicator loading">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span>Initializing scanner...</span>
                    </div>
                </div>
            </div>
            <style>
                .basic-qr-scanner {
                    position: relative;
                    width: 100%;
                    min-height: 350px;
                    background: #000;
                    border-radius: 8px;
                    overflow: hidden;
                }
                .qr-reader-container {
                    width: 100%;
                    height: 350px;
                }
                .scanner-status {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    color: white;
                    text-align: center;
                    z-index: 10;
                }
                .status-indicator {
                    padding: 20px;
                    background: rgba(0,0,0,0.8);
                    border-radius: 8px;
                }
                .status-indicator.success {
                    background: rgba(25, 135, 84, 0.9);
                }
                .status-indicator.error {
                    background: rgba(220, 53, 69, 0.9);
                }
            </style>
        `;
    }
    
    updateStatus(message, type = 'loading') {
        const statusElement = document.getElementById('scanner-status');
        if (statusElement) {
            const icon = type === 'success' ? 'fa-check' : 
                        type === 'error' ? 'fa-exclamation-triangle' : 'fa-spinner fa-spin';
            
            statusElement.innerHTML = `
                <div class="status-indicator ${type}">
                    <i class="fas ${icon}"></i>
                    <span>${message}</span>
                </div>
            `;
            
            if (type === 'success') {
                setTimeout(() => {
                    statusElement.style.display = 'none';
                }, 2000);
            }
        }
    }
    
    async start() {
        if (this.isScanning) {
            console.log('Scanner already running');
            return;
        }
        
        try {
            console.log('Starting BasicQRScanner...');
            this.updateStatus('Requesting camera access...', 'loading');
            
            // Check if Html5Qrcode is available
            if (typeof Html5Qrcode === 'undefined') {
                throw new Error('Html5Qrcode library not loaded');
            }
            
            // Initialize scanner
            this.scanner = new Html5Qrcode(`${this.containerId}-reader`);
            console.log('Html5Qrcode instance created');
            
            // Get available cameras
            const cameras = await Html5Qrcode.getCameras();
            console.log('Available cameras:', cameras);
            
            if (cameras.length === 0) {
                throw new Error('No cameras found on this device');
            }
            
            this.updateStatus('Starting camera...', 'loading');
            
            // Choose camera (prefer back camera)
            let selectedCamera = cameras[0];
            for (const camera of cameras) {
                if (camera.label.toLowerCase().includes('back') || 
                    camera.label.toLowerCase().includes('rear') ||
                    camera.label.toLowerCase().includes('environment')) {
                    selectedCamera = camera;
                    break;
                }
            }
            
            console.log('Selected camera:', selectedCamera);
            
            // Start scanning with minimal config
            const config = {
                fps: 10, // Start with low FPS for reliability
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0
            };
            
            await this.scanner.start(
                selectedCamera.id,
                config,
                (decodedText, decodedResult) => {
                    console.log('QR Code scanned:', decodedText);
                    this.updateStatus('QR Code detected!', 'success');
                    
                    if (this.onSuccess) {
                        this.onSuccess(decodedText, decodedResult);
                    }
                },
                (errorMessage) => {
                    // Ignore scan errors - they happen frequently
                }
            );
            
            this.isScanning = true;
            this.updateStatus('Camera active - Position QR code in view', 'success');
            console.log('Scanner started successfully');
            
        } catch (error) {
            console.error('Scanner start error:', error);
            this.updateStatus(`Camera failed: ${error.message}`, 'error');
            throw error;
        }
    }
    
    async stop() {
        if (!this.isScanning || !this.scanner) {
            console.log('Scanner not running');
            return;
        }
        
        try {
            await this.scanner.stop();
            this.isScanning = false;
            this.updateStatus('Camera stopped', 'loading');
            console.log('Scanner stopped successfully');
        } catch (error) {
            console.error('Scanner stop error:', error);
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
        console.log('Success callback set');
    }
}

// Global availability
window.BasicQRScanner = BasicQRScanner;
console.log('BasicQRScanner class loaded');