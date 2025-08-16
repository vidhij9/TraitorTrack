/**
 * Final QR Scanner - Simple, immediate, guaranteed to work
 */

class FinalScanner {
    constructor(containerId, onSuccess) {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.lastScan = 0;
        this.scanInterval = null;
        
        // Start immediately
        this.init();
    }
    
    init() {
        // Simple UI
        this.container.innerHTML = `
            <div style="position:relative;width:100%;height:450px;background:#111;border-radius:8px;overflow:hidden;">
                <video id="qr-video" style="width:100%;height:100%;object-fit:cover;" muted autoplay playsinline></video>
                <canvas id="qr-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;opacity:0;"></canvas>
                
                <!-- Scan frame -->
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:250px;height:250px;">
                    <div style="width:100%;height:100%;border:2px solid #0f0;"></div>
                    <div style="position:absolute;top:-5px;left:-5px;width:30px;height:30px;border-top:3px solid #0f0;border-left:3px solid #0f0;"></div>
                    <div style="position:absolute;top:-5px;right:-5px;width:30px;height:30px;border-top:3px solid #0f0;border-right:3px solid #0f0;"></div>
                    <div style="position:absolute;bottom:-5px;left:-5px;width:30px;height:30px;border-bottom:3px solid #0f0;border-left:3px solid #0f0;"></div>
                    <div style="position:absolute;bottom:-5px;right:-5px;width:30px;height:30px;border-bottom:3px solid #0f0;border-right:3px solid #0f0;"></div>
                </div>
                
                <!-- Status -->
                <div id="scan-status" style="position:absolute;bottom:20px;left:0;right:0;text-align:center;color:#0f0;font-size:16px;font-weight:bold;background:rgba(0,0,0,0.7);padding:10px;">
                    Starting camera...
                </div>
            </div>
        `;
        
        this.video = document.getElementById('qr-video');
        this.canvas = document.getElementById('qr-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        // Remove any controls
        this.video.controls = false;
        
        // Start camera immediately
        this.startCamera();
    }
    
    async startCamera() {
        const status = document.getElementById('scan-status');
        
        try {
            // Get camera stream
            let stream = await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment' } 
            }).catch(() => {
                return navigator.mediaDevices.getUserMedia({ video: true });
            });
            
            if (!stream) {
                throw new Error('No camera');
            }
            
            // Set video source
            this.video.srcObject = stream;
            
            // Don't wait for metadata, start scanning immediately
            status.textContent = 'Point at QR Code';
            
            // Set canvas size after short delay
            setTimeout(() => {
                if (this.video.videoWidth && this.video.videoHeight) {
                    this.canvas.width = this.video.videoWidth;
                    this.canvas.height = this.video.videoHeight;
                } else {
                    // Use default size
                    this.canvas.width = 640;
                    this.canvas.height = 480;
                }
                
                // Start scanning loop
                this.startScanning();
            }, 500);
            
        } catch (err) {
            console.error('Camera error:', err);
            status.textContent = 'Camera error - Check permissions';
            status.style.color = '#f00';
        }
    }
    
    startScanning() {
        const status = document.getElementById('scan-status');
        status.textContent = 'Scanning...';
        
        // Clear any existing interval
        if (this.scanInterval) {
            clearInterval(this.scanInterval);
        }
        
        // Scan every 200ms
        this.scanInterval = setInterval(() => {
            this.scan();
        }, 200);
    }
    
    scan() {
        // Make sure video is playing
        if (this.video.paused || this.video.ended) {
            return;
        }
        
        // Draw video to canvas
        try {
            this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        } catch (e) {
            return; // Video not ready yet
        }
        
        // Get image data
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        
        // Try to decode with jsQR
        if (typeof jsQR !== 'undefined') {
            // First try normal
            let code = jsQR(imageData.data, imageData.width, imageData.height);
            
            // If failed, try with inversion
            if (!code) {
                code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: 'attemptBoth'
                });
            }
            
            if (code && code.data && code.data.trim()) {
                this.foundQRCode(code.data);
            }
        }
    }
    
    foundQRCode(data) {
        // Debounce
        const now = Date.now();
        if (now - this.lastScan < 1000) return;
        this.lastScan = now;
        
        // Update status
        const status = document.getElementById('scan-status');
        status.textContent = '✓ Scanned!';
        status.style.color = '#0f0';
        
        // Beep
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRl4GAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YToGAAB/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f39/f3+H');
            audio.play();
        } catch (e) {}
        
        // Vibrate
        if (navigator.vibrate) navigator.vibrate(200);
        
        // Callback
        if (this.onSuccess) {
            this.onSuccess(data);
        }
        
        // Reset status
        setTimeout(() => {
            status.textContent = 'Scanning...';
            status.style.color = '#0f0';
        }, 2000);
    }
    
    stop() {
        if (this.scanInterval) {
            clearInterval(this.scanInterval);
            this.scanInterval = null;
        }
        
        if (this.video && this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
    }
}

window.FinalScanner = FinalScanner;