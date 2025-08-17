/**
 * Simple Reliable QR Scanner
 * =========================
 * Minimal dependencies, maximum reliability
 */

class SimpleReliableScanner {
    constructor(containerId, onSuccess) {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.scanning = false;
        this.lastScan = '';
        this.lastScanTime = 0;
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.stream = null;
        
        this.init();
    }
    
    init() {
        // Clear container and create simple UI
        this.container.innerHTML = `
            <div style="position:relative;width:100%;max-width:640px;margin:0 auto;">
                <video id="simple-video" autoplay playsinline muted 
                       style="width:100%;height:400px;object-fit:cover;border-radius:8px;background:#000;"></video>
                
                <canvas id="simple-canvas" style="display:none;"></canvas>
                
                <!-- Simple scan overlay -->
                <div style="position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;">
                    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:250px;height:250px;border:3px solid #00ff00;border-radius:8px;"></div>
                </div>
                
                <!-- Status -->
                <div style="position:absolute;bottom:10px;left:0;right:0;text-align:center;">
                    <div id="simple-status" style="color:#00ff00;font-weight:bold;background:rgba(0,0,0,0.8);padding:8px;border-radius:4px;">
                        Initializing...
                    </div>
                </div>
            </div>
        `;
        
        this.setupElements();
        this.startCamera();
    }
    
    setupElements() {
        this.video = document.getElementById('simple-video');
        this.canvas = document.getElementById('simple-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.status = document.getElementById('simple-status');
    }
    
    async startCamera() {
        try {
            this.updateStatus('Starting camera...', '#ffa500');
            
            // Simple camera constraints
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            
            this.video.onloadedmetadata = () => {
                this.video.play();
                this.startScanning();
            };
            
        } catch (error) {
            console.error('Camera error:', error);
            this.updateStatus('Camera error - Check permissions', '#ff0000');
        }
    }
    
    startScanning() {
        if (this.scanning) return;
        this.scanning = true;
        this.updateStatus('Scanning for QR codes...', '#00ff00');
        this.scanLoop();
    }
    
    scanLoop() {
        if (!this.scanning || !this.video || this.video.readyState !== 4) {
            if (this.scanning) {
                requestAnimationFrame(() => this.scanLoop());
            }
            return;
        }
        
        try {
            // Set canvas size to video size
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            
            if (this.canvas.width > 0 && this.canvas.height > 0) {
                // Draw video frame to canvas
                this.ctx.drawImage(this.video, 0, 0);
                
                // Get image data and scan
                const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
                
                // Check if jsQR is available
                if (typeof jsQR !== 'undefined') {
                    const code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: "attemptBoth"
                    });
                    
                    if (code && code.data) {
                        this.handleSuccess(code.data);
                        return;
                    }
                }
            }
            
        } catch (error) {
            console.error('Scan error:', error);
        }
        
        // Continue scanning
        requestAnimationFrame(() => this.scanLoop());
    }
    
    handleSuccess(qrData) {
        // Prevent duplicate scans
        const now = Date.now();
        if (qrData === this.lastScan && (now - this.lastScanTime) < 1000) {
            return;
        }
        
        this.lastScan = qrData;
        this.lastScanTime = now;
        
        console.log('QR Code detected:', qrData);
        
        // Visual feedback
        this.updateStatus('✅ QR Code Detected!', '#00ff00');
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([100, 50, 100]);
        }
        
        // Callback
        if (this.onSuccess) {
            this.onSuccess(qrData);
        }
        
        // Resume scanning after brief pause
        setTimeout(() => {
            this.updateStatus('Scanning for QR codes...', '#00ff00');
        }, 1500);
    }
    
    updateStatus(message, color = '#00ff00') {
        if (this.status) {
            this.status.textContent = message;
            this.status.style.color = color;
        }
    }
    
    stop() {
        this.scanning = false;
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
    }
}

// Make available globally
window.SimpleReliableScanner = SimpleReliableScanner;