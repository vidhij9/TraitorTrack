/**
 * Working QR Scanner - Simple, fast, and reliable
 * Focuses on what works: jsQR with basic preprocessing
 */

class WorkingScanner {
    constructor(containerId, onSuccess, scanType = 'unknown') {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.scanType = scanType;
        this.lastScan = '';
        this.lastScanTime = 0;
        this.scanning = false;
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div style="position:relative;width:100%;height:400px;background:#000;border-radius:8px;overflow:hidden;">
                <video id="qr-video" style="width:100%;height:100%;object-fit:cover;" muted autoplay playsinline></video>
                <canvas id="qr-canvas" style="display:none;"></canvas>
                
                <!-- Scan frame -->
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:250px;height:250px;">
                    <div style="width:100%;height:100%;border:3px solid #0f0;"></div>
                    <div style="position:absolute;top:-3px;left:-3px;width:30px;height:30px;border-top:4px solid #0f0;border-left:4px solid #0f0;"></div>
                    <div style="position:absolute;top:-3px;right:-3px;width:30px;height:30px;border-top:4px solid #0f0;border-right:4px solid #0f0;"></div>
                    <div style="position:absolute;bottom:-3px;left:-3px;width:30px;height:30px;border-bottom:4px solid #0f0;border-left:4px solid #0f0;"></div>
                    <div style="position:absolute;bottom:-3px;right:-3px;width:30px;height:30px;border-bottom:4px solid #0f0;border-right:4px solid #0f0;"></div>
                </div>
                
                <!-- Status -->
                <div id="scan-status" style="position:absolute;bottom:10px;left:0;right:0;text-align:center;color:#0f0;font-weight:bold;background:rgba(0,0,0,0.7);padding:10px;">
                    Initializing...
                </div>
                
                <!-- Manual Entry Fallback -->
                <div style="position:absolute;top:10px;right:10px;">
                    <button onclick="window.showManualEntry()" style="background:#007bff;color:white;border:none;padding:8px 15px;border-radius:5px;cursor:pointer;font-size:14px;">
                        <i class="fas fa-keyboard"></i> Manual
                    </button>
                </div>
            </div>
            
            <!-- Manual Entry (Hidden) -->
            <div id="manual-entry" style="display:none;padding:15px;background:#f8f9fa;border-radius:8px;margin-top:10px;">
                <h5>Manual QR Entry</h5>
                <div class="input-group">
                    <input type="text" id="manual-input" class="form-control" placeholder="Enter QR code">
                    <button class="btn btn-success" onclick="window.submitManual()">Submit</button>
                    <button class="btn btn-secondary" onclick="window.hideManualEntry()">Cancel</button>
                </div>
            </div>
        `;
        
        this.video = document.getElementById('qr-video');
        this.canvas = document.getElementById('qr-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.status = document.getElementById('scan-status');
        
        // Setup global functions for onclick handlers
        window.showManualEntry = () => this.showManualEntry();
        window.hideManualEntry = () => this.hideManualEntry();
        window.submitManual = () => this.submitManual();
        
        this.startCamera();
    }
    
    async startCamera() {
        try {
            // Simple camera request
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            }).catch(() => {
                // Fallback to any camera
                return navigator.mediaDevices.getUserMedia({ video: true });
            });
            
            this.video.srcObject = stream;
            
            // Wait for video to be ready
            this.video.onloadedmetadata = () => {
                this.video.play();
                this.canvas.width = Math.min(640, this.video.videoWidth);
                this.canvas.height = Math.min(480, this.video.videoHeight);
                this.status.textContent = 'Ready - Point at QR Code';
                this.startScanning();
            };
            
        } catch (err) {
            console.error('Camera error:', err);
            this.status.textContent = 'Camera Error - Use Manual Entry';
            this.status.style.color = '#f00';
            this.showManualEntry();
        }
    }
    
    startScanning() {
        this.scanning = true;
        this.scanLoop();
    }
    
    scanLoop() {
        if (!this.scanning) return;
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            // Draw frame to canvas
            this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            
            // Get image data
            const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // Try jsQR decoding
            if (typeof jsQR !== 'undefined') {
                // Try normal scan
                let code = jsQR(imageData.data, imageData.width, imageData.height);
                
                // If failed, try with inversion
                if (!code) {
                    code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: 'attemptBoth'
                    });
                }
                
                // If we found a code
                if (code && code.data && code.data.trim()) {
                    this.handleScan(code.data.trim());
                }
            }
        }
        
        // Continue scanning
        requestAnimationFrame(() => this.scanLoop());
    }
    
    handleScan(qrCode) {
        // Prevent duplicate scans within 1 second
        const now = Date.now();
        if (qrCode === this.lastScan && (now - this.lastScanTime) < 1000) {
            return;
        }
        
        this.lastScan = qrCode;
        this.lastScanTime = now;
        
        // Update UI
        this.status.textContent = `✓ Scanned: ${qrCode}`;
        this.status.style.color = '#0f0';
        
        // Audio feedback
        try {
            const beep = new Audio('data:audio/wav;base64,UklGRl4GAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YToGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUand7blmFgU7k9n1unEiBC13yO/eizEIHWq+8+OWT');
            beep.play();
        } catch {}
        
        // Vibrate
        if (navigator.vibrate) navigator.vibrate(100);
        
        // Call success handler
        if (this.onSuccess) {
            this.onSuccess(qrCode);
        }
        
        // Reset status after delay
        setTimeout(() => {
            this.status.textContent = 'Scanning...';
            this.status.style.color = '#0f0';
        }, 2000);
    }
    
    showManualEntry() {
        document.getElementById('manual-entry').style.display = 'block';
        document.getElementById('manual-input').focus();
    }
    
    hideManualEntry() {
        document.getElementById('manual-entry').style.display = 'none';
        document.getElementById('manual-input').value = '';
    }
    
    submitManual() {
        const input = document.getElementById('manual-input').value.trim();
        if (input) {
            this.handleScan(input);
            this.hideManualEntry();
        }
    }
    
    stop() {
        this.scanning = false;
        if (this.video && this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
    }
}

// Enhanced scanner with preprocessing (optional)
class EnhancedScanner extends WorkingScanner {
    constructor(containerId, onSuccess, scanType = 'unknown') {
        super(containerId, onSuccess, scanType);
        this.enhanceCanvas = document.createElement('canvas');
        this.enhanceCtx = this.enhanceCanvas.getContext('2d');
        this.enhanceCanvas.width = 640;
        this.enhanceCanvas.height = 480;
    }
    
    scanLoop() {
        if (!this.scanning) return;
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            // Draw frame to canvas
            this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            
            // Get original image data
            let imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // Try normal jsQR first
            if (typeof jsQR !== 'undefined') {
                let code = jsQR(imageData.data, imageData.width, imageData.height);
                
                if (!code) {
                    // Try with inversion
                    code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: 'attemptBoth'
                    });
                }
                
                if (!code) {
                    // Try with preprocessing
                    imageData = this.preprocessImage(imageData);
                    code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: 'attemptBoth'
                    });
                }
                
                if (code && code.data && code.data.trim()) {
                    this.handleScan(code.data.trim());
                }
            }
        }
        
        // Continue scanning
        requestAnimationFrame(() => this.scanLoop());
    }
    
    preprocessImage(imageData) {
        const data = imageData.data;
        
        // Convert to grayscale and enhance contrast
        for (let i = 0; i < data.length; i += 4) {
            const gray = data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
            
            // Apply contrast enhancement
            let enhanced = ((gray - 128) * 1.5) + 128;
            enhanced = Math.max(0, Math.min(255, enhanced));
            
            // Apply threshold for better black/white separation
            const threshold = enhanced > 127 ? 255 : 0;
            
            data[i] = threshold;
            data[i + 1] = threshold;
            data[i + 2] = threshold;
        }
        
        return imageData;
    }
}

window.WorkingScanner = WorkingScanner;
window.EnhancedScanner = EnhancedScanner;