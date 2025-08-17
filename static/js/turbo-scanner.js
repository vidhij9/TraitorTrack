/**
 * Turbo Scanner - Maximum Speed & Reliability
 * ============================================
 * Simplified for instant detection within 1 second
 */

class TurboScanner {
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
        // Clear container
        this.container.innerHTML = '';
        
        this.container.innerHTML = `
            <div style="position:relative;width:100%;max-width:500px;margin:0 auto;">
                <video id="turbo-video" autoplay playsinline muted 
                       style="width:100%;height:400px;object-fit:cover;border-radius:8px;background:#000;"></video>
                
                <canvas id="turbo-canvas" style="display:none;"></canvas>
                
                <!-- Simple overlay -->
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:250px;height:250px;border:3px solid #00ff00;border-radius:8px;pointer-events:none;">
                    <div style="position:absolute;top:-5px;left:-5px;width:40px;height:40px;border-left:4px solid #00ff00;border-top:4px solid #00ff00;"></div>
                    <div style="position:absolute;top:-5px;right:-5px;width:40px;height:40px;border-right:4px solid #00ff00;border-top:4px solid #00ff00;"></div>
                    <div style="position:absolute;bottom:-5px;left:-5px;width:40px;height:40px;border-left:4px solid #00ff00;border-bottom:4px solid #00ff00;"></div>
                    <div style="position:absolute;bottom:-5px;right:-5px;width:40px;height:40px;border-right:4px solid #00ff00;border-bottom:4px solid #00ff00;"></div>
                </div>
                
                <!-- Status -->
                <div style="position:absolute;bottom:10px;left:0;right:0;text-align:center;">
                    <div id="turbo-status" style="color:#00ff00;background:rgba(0,0,0,0.8);padding:8px 16px;border-radius:20px;display:inline-block;">
                        Starting...
                    </div>
                </div>
            </div>
        `;
        
        this.setupElements();
        this.startCamera();
    }
    
    setupElements() {
        this.video = document.getElementById('turbo-video');
        this.canvas = document.getElementById('turbo-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.status = document.getElementById('turbo-status');
    }
    
    async startCamera() {
        try {
            this.status.textContent = 'Starting camera...';
            
            // Simple constraints for faster initialization
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 800 }, // Lower resolution for faster processing
                    height: { ideal: 600 }
                }
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints)
                .catch(() => navigator.mediaDevices.getUserMedia({ video: true }));
            
            this.video.srcObject = this.stream;
            
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play().then(resolve);
                };
            });
            
            this.status.textContent = 'Ready - Point at QR';
            this.startScanning();
            
        } catch (error) {
            console.error('Camera error:', error);
            this.status.textContent = 'Camera error';
        }
    }
    
    startScanning() {
        if (this.scanning) return;
        this.scanning = true;
        
        const scan = () => {
            if (!this.scanning) return;
            
            if (this.video.readyState === 4) {
                const width = this.video.videoWidth;
                const height = this.video.videoHeight;
                
                if (width && height) {
                    // Set canvas size once
                    if (this.canvas.width !== width) {
                        this.canvas.width = width;
                        this.canvas.height = height;
                    }
                    
                    // Draw frame
                    this.ctx.drawImage(this.video, 0, 0, width, height);
                    
                    // Get image data and scan
                    const imageData = this.ctx.getImageData(0, 0, width, height);
                    
                    // Try jsQR with both normal and inverted
                    const code = jsQR(imageData.data, width, height, {
                        inversionAttempts: 'attemptBoth'
                    });
                    
                    if (code && code.data) {
                        this.handleSuccess(code.data);
                    }
                }
            }
            
            // Continue scanning
            requestAnimationFrame(scan);
        };
        
        scan();
    }
    
    handleSuccess(qrData) {
        // Prevent duplicates
        const now = Date.now();
        if (qrData === this.lastScan && (now - this.lastScanTime) < 500) {
            return;
        }
        
        this.lastScan = qrData;
        this.lastScanTime = now;
        
        console.log('Turbo detected:', qrData);
        
        // Update status
        this.status.textContent = '✓ Detected!';
        this.status.style.color = '#00ff00';
        
        // Quick beep
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAECcAABBnAAACABAAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBTGH0fPTgjMGHm7A7+OZURE');
            audio.play();
        } catch (e) {}
        
        // Vibrate
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
        
        // Callback
        if (this.onSuccess) {
            this.onSuccess(qrData);
        }
        
        // Reset status quickly
        setTimeout(() => {
            this.status.textContent = 'Ready - Point at QR';
            this.status.style.color = '#00ff00';
        }, 500);
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
        
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Make available globally
window.TurboScanner = TurboScanner;