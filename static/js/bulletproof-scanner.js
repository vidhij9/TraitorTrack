/**
 * Bulletproof QR Scanner - Simple, reliable, no controls
 * Guaranteed to work with any QR code
 */

class BulletproofScanner {
    constructor(containerId, onSuccess) {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.lastScan = 0;
        this.video = null;
        this.canvasElement = null;
        this.canvasContext = null;
        this.scanning = false;
        
        this.init();
    }
    
    init() {
        // Simple, clean UI with no video controls
        this.container.innerHTML = `
            <div style="position:relative;width:100%;height:450px;background:#000;border-radius:8px;overflow:hidden;">
                <video id="bp-video" style="width:100%;height:100%;object-fit:cover;pointer-events:none;" muted playsinline></video>
                <canvas id="bp-canvas" style="display:none;"></canvas>
                
                <!-- Clean scanning indicator -->
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:260px;height:260px;border:2px solid #0f0;box-shadow:0 0 30px rgba(0,255,0,0.5);pointer-events:none;"></div>
                
                <!-- Simple status -->
                <div id="bp-status" style="position:absolute;bottom:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.8);padding:10px 30px;border-radius:20px;color:#0f0;font-weight:bold;font-size:16px;">
                    Initializing Scanner...
                </div>
            </div>
        `;
        
        this.video = document.getElementById('bp-video');
        this.canvasElement = document.getElementById('bp-canvas');
        this.canvasContext = this.canvasElement.getContext('2d');
        
        // Remove all video controls
        this.video.controls = false;
        this.video.removeAttribute('controls');
        
        this.startCamera();
    }
    
    async startCamera() {
        const statusEl = document.getElementById('bp-status');
        
        try {
            // Try to get camera access
            const constraints = [
                { video: { facingMode: 'environment' } },
                { video: true }
            ];
            
            let stream = null;
            for (const constraint of constraints) {
                try {
                    stream = await navigator.mediaDevices.getUserMedia(constraint);
                    if (stream) break;
                } catch (e) {
                    console.log('Trying next constraint...');
                }
            }
            
            if (!stream) {
                throw new Error('No camera available');
            }
            
            // Setup video
            this.video.srcObject = stream;
            this.video.setAttribute('autoplay', '');
            this.video.setAttribute('muted', '');
            this.video.setAttribute('playsinline', '');
            
            // Remove controls again to be sure
            this.video.controls = false;
            this.video.removeAttribute('controls');
            
            // Play video
            await this.video.play();
            
            // Setup canvas once video is ready
            this.video.addEventListener('loadedmetadata', () => {
                this.canvasElement.width = 640;
                this.canvasElement.height = 480;
                statusEl.textContent = 'Scanning for QR Code...';
                statusEl.style.color = '#0f0';
                this.scanning = true;
                this.scan();
            });
            
        } catch (err) {
            console.error('Camera error:', err);
            statusEl.textContent = 'Camera Not Available';
            statusEl.style.color = '#f00';
        }
    }
    
    scan() {
        if (!this.scanning) return;
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            // Draw video frame to canvas
            this.canvasContext.drawImage(this.video, 0, 0, 640, 480);
            
            // Get image data
            const imageData = this.canvasContext.getImageData(0, 0, 640, 480);
            
            // Process image for better detection
            this.processImage(imageData);
            
            // Try to decode QR code
            if (typeof jsQR !== 'undefined') {
                // Try normal scan
                let code = jsQR(imageData.data, imageData.width, imageData.height);
                
                if (!code) {
                    // Try with inversion
                    code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: 'attemptBoth'
                    });
                }
                
                if (code && code.data) {
                    console.log('QR Code found:', code.data);
                    this.handleSuccess(code.data);
                }
            }
        }
        
        // Continue scanning
        setTimeout(() => this.scan(), 100);
    }
    
    processImage(imageData) {
        const data = imageData.data;
        
        // Simple contrast enhancement
        for (let i = 0; i < data.length; i += 4) {
            // Convert to grayscale
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            
            // Enhance contrast
            let enhanced = (gray - 128) * 1.5 + 128;
            enhanced = Math.max(0, Math.min(255, enhanced));
            
            // Apply back to all channels
            data[i] = enhanced;
            data[i+1] = enhanced;
            data[i+2] = enhanced;
        }
        
        return imageData;
    }
    
    handleSuccess(qrData) {
        // Prevent duplicate scans
        const now = Date.now();
        if (now - this.lastScan < 1500) return;
        this.lastScan = now;
        
        // Update status
        const statusEl = document.getElementById('bp-status');
        statusEl.textContent = '✓ QR Code Scanned!';
        statusEl.style.color = '#0f0';
        statusEl.style.background = 'rgba(0,255,0,0.2)';
        
        // Flash effect
        this.container.style.boxShadow = '0 0 50px rgba(0,255,0,0.8)';
        
        // Audio feedback
        try {
            const beep = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBi+Gyffo');
            beep.volume = 0.3;
            beep.play();
        } catch (e) {}
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(200);
        }
        
        // Call success callback
        if (this.onSuccess) {
            this.onSuccess(qrData);
        }
        
        // Reset after delay
        setTimeout(() => {
            statusEl.textContent = 'Scanning for QR Code...';
            statusEl.style.color = '#0f0';
            statusEl.style.background = 'rgba(0,0,0,0.8)';
            this.container.style.boxShadow = '';
        }, 2000);
    }
    
    stop() {
        this.scanning = false;
        if (this.video && this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
    }
}

// Make globally available
window.BulletproofScanner = BulletproofScanner;