/**
 * Simple QR Scanner - Direct camera access without complex dependencies
 * Focuses on getting the camera working reliably
 */

class SimpleQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.isScanning = false;
        this.onSuccess = null;
        this.stream = null;
        
        console.log('SimpleQR: Initializing...');
        this.init();
    }
    
    init() {
        this.setupUI();
        this.setupElements();
        setTimeout(() => this.startCamera(), 500);
    }
    
    setupUI() {
        this.container.innerHTML = `
            <div class="simple-scanner" style="position: relative; width: 100%; height: 400px; background: #000; border-radius: 8px; overflow: hidden;">
                <video id="${this.containerId}-video" autoplay playsinline muted style="width: 100%; height: 100%; object-fit: cover;"></video>
                <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
                
                <!-- Simple overlay -->
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 200px; height: 200px; border: 2px solid #fff; border-radius: 8px; pointer-events: none;"></div>
                
                <!-- Status -->
                <div id="${this.containerId}-status" style="position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.7); color: white; padding: 8px 16px; border-radius: 4px; text-align: center;">
                    Starting camera...
                </div>
            </div>
        `;
    }
    
    setupElements() {
        this.video = document.getElementById(`${this.containerId}-video`);
        this.canvas = document.getElementById(`${this.containerId}-canvas`);
        this.context = this.canvas.getContext('2d');
        this.statusDiv = document.getElementById(`${this.containerId}-status`);
    }
    
    updateStatus(message, type = 'info') {
        console.log(`SimpleQR: ${message}`);
        if (this.statusDiv) {
            this.statusDiv.textContent = message;
            this.statusDiv.style.background = type === 'error' ? 'rgba(220,20,20,0.8)' : 
                                           type === 'success' ? 'rgba(20,220,20,0.8)' : 
                                           'rgba(0,0,0,0.7)';
        }
    }
    
    async startCamera() {
        try {
            this.updateStatus('Requesting camera permission...');
            
            // Simple camera constraints
            const constraints = {
                video: {
                    facingMode: 'environment', // Back camera
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                },
                audio: false
            };
            
            console.log('SimpleQR: Requesting camera access...');
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            
            console.log('SimpleQR: Camera stream obtained');
            this.video.srcObject = this.stream;
            
            this.video.onloadedmetadata = () => {
                console.log('SimpleQR: Video metadata loaded');
                this.video.play().then(() => {
                    console.log('SimpleQR: Video playing');
                    this.updateStatus('Camera active - Position QR code in frame', 'success');
                    this.startScanning();
                }).catch(err => {
                    console.error('SimpleQR: Video play failed:', err);
                    this.updateStatus('Video play failed: ' + err.message, 'error');
                });
            };
            
        } catch (error) {
            console.error('SimpleQR: Camera error:', error);
            this.updateStatus('Camera access failed: ' + error.message, 'error');
            
            // Show manual entry prompt
            setTimeout(() => {
                this.updateStatus('Use manual entry below', 'info');
                this.showManualPrompt();
            }, 3000);
        }
    }
    
    startScanning() {
        if (!this.isScanning && typeof jsQR !== 'undefined') {
            this.isScanning = true;
            console.log('SimpleQR: Starting QR detection...');
            this.scan();
        } else if (typeof jsQR === 'undefined') {
            console.error('SimpleQR: jsQR library not loaded');
            this.updateStatus('QR detection library not loaded', 'error');
        }
    }
    
    scan() {
        if (!this.isScanning || !this.video || this.video.readyState !== 4) {
            if (this.isScanning) {
                requestAnimationFrame(() => this.scan());
            }
            return;
        }
        
        try {
            // Set canvas size
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            
            if (this.canvas.width > 0 && this.canvas.height > 0) {
                // Draw current video frame
                this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                
                // Get image data
                const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
                
                // Scan for QR code
                const code = jsQR(imageData.data, imageData.width, imageData.height);
                
                if (code && code.data) {
                    console.log('SimpleQR: QR code detected:', code.data);
                    this.handleSuccess(code.data);
                    return;
                }
            }
            
        } catch (error) {
            console.error('SimpleQR: Scan error:', error);
        }
        
        // Continue scanning
        if (this.isScanning) {
            requestAnimationFrame(() => this.scan());
        }
    }
    
    handleSuccess(qrData) {
        this.updateStatus('QR Code found: ' + qrData, 'success');
        
        // Vibrate if supported
        if (navigator.vibrate) {
            navigator.vibrate(100);
        }
        
        // Call success callback
        if (this.onSuccess && typeof this.onSuccess === 'function') {
            this.onSuccess(qrData);
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
    
    showManualPrompt() {
        const resultContainer = document.getElementById('result-container');
        if (resultContainer) {
            resultContainer.className = 'alert alert-warning';
            resultContainer.innerHTML = '<i class="fas fa-keyboard me-2"></i>Camera not available. Please use manual entry below.';
        }
    }
    
    stop() {
        this.isScanning = false;
        
        if (this.stream) {
            const tracks = this.stream.getTracks();
            tracks.forEach(track => track.stop());
            this.stream = null;
            console.log('SimpleQR: Camera stopped');
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
    }
}

// Export
window.SimpleQRScanner = SimpleQRScanner;
console.log('SimpleQRScanner loaded');