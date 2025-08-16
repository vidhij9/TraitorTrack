/**
 * Instant QR Scanner - Ultra-optimized for speed and consistency
 * Target: < 1 second scan time, 100+ concurrent users
 */

class InstantScanner {
    constructor(containerId, onSuccess) {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.scanning = false;
        this.lastScan = '';
        this.scanCount = 0;
        
        // Performance settings
        this.frameSkip = 0;
        this.targetFPS = 30;
        this.scanRegionSize = 0.5; // Scan only center 50% for speed
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div style="position:relative;width:100%;height:400px;background:#000;overflow:hidden;border-radius:8px;">
                <video id="qr-video" style="width:100%;height:100%;object-fit:cover;" muted autoplay playsinline></video>
                <canvas id="qr-canvas" style="display:none;"></canvas>
                
                <!-- Optimized scan region indicator -->
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:200px;height:200px;border:2px solid #0f0;opacity:0.8;">
                    <div style="position:absolute;top:-2px;left:-2px;width:20px;height:20px;border-top:4px solid #0f0;border-left:4px solid #0f0;"></div>
                    <div style="position:absolute;top:-2px;right:-2px;width:20px;height:20px;border-top:4px solid #0f0;border-right:4px solid #0f0;"></div>
                    <div style="position:absolute;bottom:-2px;left:-2px;width:20px;height:20px;border-bottom:4px solid #0f0;border-left:4px solid #0f0;"></div>
                    <div style="position:absolute;bottom:-2px;right:-2px;width:20px;height:20px;border-bottom:4px solid #0f0;border-right:4px solid #0f0;"></div>
                </div>
                
                <div id="scan-status" style="position:absolute;bottom:10px;left:0;right:0;text-align:center;color:#0f0;font-weight:bold;font-size:14px;background:rgba(0,0,0,0.7);padding:8px;">
                    Initializing...
                </div>
            </div>
        `;
        
        this.video = document.getElementById('qr-video');
        this.canvas = document.getElementById('qr-canvas');
        this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
        this.status = document.getElementById('scan-status');
        
        this.startCamera();
    }
    
    async startCamera() {
        try {
            // Request camera with optimal settings for speed
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    frameRate: { ideal: 30 }
                }
            };
            
            const stream = await navigator.mediaDevices.getUserMedia(constraints)
                .catch(() => navigator.mediaDevices.getUserMedia({ video: true }));
            
            this.video.srcObject = stream;
            
            // Start scanning immediately, don't wait for metadata
            this.video.play();
            this.status.textContent = 'Ready - Point at QR Code';
            
            // Set optimal canvas size after 100ms
            setTimeout(() => {
                // Use smaller canvas for faster processing
                this.canvas.width = 640;
                this.canvas.height = 480;
                this.startScanning();
            }, 100);
            
        } catch (err) {
            console.error('Camera error:', err);
            this.status.textContent = 'Camera Error - Check Permissions';
            this.status.style.color = '#f00';
        }
    }
    
    startScanning() {
        if (this.scanning) return;
        this.scanning = true;
        this.status.textContent = 'Scanning...';
        this.scanLoop();
    }
    
    scanLoop() {
        if (!this.scanning) return;
        
        // Skip frames for performance
        this.frameSkip++;
        if (this.frameSkip % 2 === 0) {
            requestAnimationFrame(() => this.scanLoop());
            return;
        }
        
        try {
            // Check if video is ready
            if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
                // Draw only center region for faster processing
                const vw = this.video.videoWidth;
                const vh = this.video.videoHeight;
                
                if (vw && vh) {
                    // Calculate center region
                    const regionSize = this.scanRegionSize;
                    const sx = vw * (1 - regionSize) / 2;
                    const sy = vh * (1 - regionSize) / 2;
                    const sw = vw * regionSize;
                    const sh = vh * regionSize;
                    
                    // Draw center region to smaller canvas
                    this.ctx.drawImage(this.video, sx, sy, sw, sh, 0, 0, this.canvas.width, this.canvas.height);
                    
                    // Get image data
                    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
                    
                    // Try to decode QR code
                    if (typeof jsQR !== 'undefined') {
                        // Fast decode with minimal processing
                        const code = jsQR(imageData.data, imageData.width, imageData.height, {
                            inversionAttempts: 'dontInvert' // Fastest option
                        });
                        
                        if (code && code.data) {
                            this.handleScan(code.data);
                        } else {
                            // Try with inversion as fallback (only every 10th frame)
                            if (this.scanCount % 10 === 0) {
                                const codeInverted = jsQR(imageData.data, imageData.width, imageData.height, {
                                    inversionAttempts: 'onlyInvert'
                                });
                                if (codeInverted && codeInverted.data) {
                                    this.handleScan(codeInverted.data);
                                }
                            }
                        }
                    }
                }
            }
        } catch (e) {
            // Silently continue
        }
        
        this.scanCount++;
        
        // Continue scanning
        requestAnimationFrame(() => this.scanLoop());
    }
    
    handleScan(data) {
        // Deduplicate
        if (data === this.lastScan) return;
        
        const now = Date.now();
        if (this.lastScanTime && (now - this.lastScanTime) < 500) return;
        
        this.lastScan = data;
        this.lastScanTime = now;
        
        // Visual feedback
        this.status.textContent = '✓ Scanned!';
        this.status.style.color = '#0f0';
        
        // Audio feedback
        try {
            const beep = new Audio('data:audio/wav;base64,UklGRl4GAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YToGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUand7blmFgU7k9n1unEiBC13yO/eizEIHWq+8+OWT');
            beep.play();
        } catch {}
        
        // Haptic feedback
        if (navigator.vibrate) navigator.vibrate(100);
        
        // Callback
        if (this.onSuccess) {
            this.onSuccess(data);
        }
        
        // Reset status
        setTimeout(() => {
            this.status.textContent = 'Scanning...';
            this.status.style.color = '#0f0';
        }, 1500);
    }
    
    stop() {
        this.scanning = false;
        if (this.video && this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
    }
}

// Fallback scanner using QR Scanner library if jsQR fails
class QRScannerFallback {
    constructor(containerId, onSuccess) {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.init();
    }
    
    init() {
        // Load QR Scanner library dynamically
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/qr-scanner@1.4.2/qr-scanner.umd.min.js';
        script.onload = () => this.setupScanner();
        document.head.appendChild(script);
    }
    
    setupScanner() {
        this.container.innerHTML = `
            <video id="qr-video-fallback" style="width:100%;height:400px;object-fit:cover;border-radius:8px;"></video>
        `;
        
        const video = document.getElementById('qr-video-fallback');
        
        // Use QR Scanner library for better performance
        this.qrScanner = new QrScanner(
            video,
            result => this.onSuccess(result.data),
            {
                preferredCamera: 'environment',
                highlightScanRegion: true,
                highlightCodeOutline: true,
                maxScansPerSecond: 10
            }
        );
        
        this.qrScanner.start();
    }
    
    stop() {
        if (this.qrScanner) {
            this.qrScanner.stop();
        }
    }
}

window.InstantScanner = InstantScanner;
window.QRScannerFallback = QRScannerFallback;