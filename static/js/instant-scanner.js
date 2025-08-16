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
        
        // Ultra-fast performance settings
        this.frameSkip = 0;
        this.targetFPS = 60; // Higher FPS for faster scanning
        this.scanRegionSize = 0.6; // Scan center 60% for optimal balance
        this.lastFrameTime = performance.now();
        this.fpsFrames = [];
        
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
        this.ctx = this.canvas.getContext('2d', { 
            willReadFrequently: true,
            alpha: false,
            desynchronized: true 
        });
        this.status = document.getElementById('scan-status');
        
        this.startCamera();
    }
    
    async startCamera() {
        try {
            // Request camera with optimal settings for speed
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 640 },  // Lower resolution for speed
                    height: { ideal: 480 },
                    frameRate: { ideal: 60, min: 30 }  // Higher FPS
                }
            };
            
            const stream = await navigator.mediaDevices.getUserMedia(constraints)
                .catch(() => navigator.mediaDevices.getUserMedia({ video: true }));
            
            this.video.srcObject = stream;
            
            // Apply performance optimizations
            const track = stream.getVideoTracks()[0];
            if (track && track.applyConstraints) {
                try {
                    await track.applyConstraints({
                        advanced: [
                            { focusMode: 'continuous' },
                            { exposureMode: 'continuous' },
                            { whiteBalanceMode: 'continuous' }
                        ]
                    });
                } catch (e) {
                    console.log('InstantScanner: Advanced constraints not supported');
                }
            }
            
            // Start scanning immediately
            await this.video.play();
            this.status.textContent = 'Ready - Point at QR Code';
            
            // Set optimal canvas size immediately
            this.canvas.width = 640;
            this.canvas.height = 480;
            this.startScanning();
            
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
        
        // Track FPS
        const currentTime = performance.now();
        const deltaTime = currentTime - this.lastFrameTime;
        this.lastFrameTime = currentTime;
        
        if (this.fpsFrames.length < 30) {
            this.fpsFrames.push(1000 / deltaTime);
        } else {
            this.fpsFrames.shift();
            this.fpsFrames.push(1000 / deltaTime);
        }
        
        // NO FRAME SKIPPING - scan every frame for maximum speed
        
        try {
            // Check if video is ready
            if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
                // Draw only center region for faster processing
                const vw = this.video.videoWidth;
                const vh = this.video.videoHeight;
                
                if (vw && vh) {
                    // Draw video directly at optimized resolution
                    this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                    
                    // Get center region for faster processing
                    const regionPixelSize = Math.floor(this.canvas.width * this.scanRegionSize);
                    const offsetX = Math.floor((this.canvas.width - regionPixelSize) / 2);
                    const offsetY = Math.floor((this.canvas.height - regionPixelSize) / 2);
                    
                    // Get image data from center region only
                    const imageData = this.ctx.getImageData(offsetX, offsetY, regionPixelSize, regionPixelSize);
                    
                    // Try to decode QR code
                    if (typeof jsQR !== 'undefined') {
                        // Ultra-fast single-pass scan
                        const code = jsQR(imageData.data, imageData.width, imageData.height, {
                            inversionAttempts: 'dontInvert' // Fastest option - no retries
                        });
                        
                        if (code && code.data) {
                            this.handleScan(code.data);
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
        if (this.lastScanTime && (now - this.lastScanTime) < 200) return;  // Shorter delay
        
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
        
        // Shorter haptic feedback
        if (navigator.vibrate) navigator.vibrate(50);
        
        // Callback
        if (this.onSuccess) {
            this.onSuccess(data);
        }
        
        // Faster reset for continuous scanning
        setTimeout(() => {
            this.status.textContent = 'Scanning...';
            this.status.style.color = '#0f0';
        }, 500);
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