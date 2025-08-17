/**
 * Google Lens Scanner - True Instant Detection
 * ==============================================
 * Zero-delay scanning with continuous detection
 */

class GoogleLensScanner {
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
        
        // Google Lens-like settings
        this.duplicateTimeout = 200; // Ultra-short for rapid scanning
        this.continuousMode = true; // Keep scanning without pause
        
        this.init();
    }
    
    init() {
        // Clear container
        this.container.innerHTML = '';
        
        this.container.innerHTML = `
            <div style="position:relative;width:100%;max-width:640px;margin:0 auto;">
                <video id="lens-video" autoplay playsinline muted 
                       style="width:100%;height:400px;object-fit:cover;border-radius:8px;background:#000;"></video>
                
                <canvas id="lens-canvas" style="display:none;"></canvas>
                
                <!-- Google Lens style overlay -->
                <div style="position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;">
                    <div id="lens-frame" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:260px;height:260px;">
                        <!-- Animated scanning dots -->
                        <div class="lens-corner" style="position:absolute;top:0;left:0;width:30px;height:30px;border-left:3px solid #4285f4;border-top:3px solid #4285f4;"></div>
                        <div class="lens-corner" style="position:absolute;top:0;right:0;width:30px;height:30px;border-right:3px solid #4285f4;border-top:3px solid #4285f4;"></div>
                        <div class="lens-corner" style="position:absolute;bottom:0;left:0;width:30px;height:30px;border-left:3px solid #4285f4;border-bottom:3px solid #4285f4;"></div>
                        <div class="lens-corner" style="position:absolute;bottom:0;right:0;width:30px;height:30px;border-right:3px solid #4285f4;border-bottom:3px solid #4285f4;"></div>
                        
                        <!-- Center dot -->
                        <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:8px;height:8px;background:#4285f4;border-radius:50%;"></div>
                    </div>
                </div>
                
                <!-- Minimal status -->
                <div style="position:absolute;bottom:10px;left:0;right:0;text-align:center;">
                    <div id="lens-status" style="color:#4285f4;font-size:12px;background:rgba(255,255,255,0.9);padding:5px 15px;border-radius:20px;display:inline-block;">
                        Scanning...
                    </div>
                </div>
                
                <style>
                .lens-corner {
                    animation: pulse 1.5s infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                </style>
            </div>
        `;
        
        this.setupElements();
        this.startCamera();
    }
    
    setupElements() {
        this.video = document.getElementById('lens-video');
        this.canvas = document.getElementById('lens-canvas');
        this.ctx = this.canvas.getContext('2d', {
            willReadFrequently: true,
            alpha: false,
            desynchronized: true
        });
        this.status = document.getElementById('lens-status');
        this.lensFrame = document.getElementById('lens-frame');
    }
    
    async startCamera() {
        try {
            // Optimized for maximum FPS
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    frameRate: { ideal: 60 } // Maximum framerate
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
            
            // Start continuous scanning immediately
            this.startContinuousScanning();
            
        } catch (error) {
            console.error('Camera error:', error);
            this.status.textContent = 'Camera error';
        }
    }
    
    startContinuousScanning() {
        if (this.scanning) return;
        this.scanning = true;
        
        // Ultra-fast continuous loop
        const continuousScan = () => {
            if (!this.scanning) return;
            
            if (this.video && this.video.readyState === 4) {
                this.ultraFastDetection();
            }
            
            // No delay - continuous scanning
            requestAnimationFrame(continuousScan);
        };
        
        continuousScan();
    }
    
    ultraFastDetection() {
        const videoWidth = this.video.videoWidth;
        const videoHeight = this.video.videoHeight;
        
        if (!videoWidth || !videoHeight) return;
        
        // Update canvas size once
        if (this.canvas.width !== videoWidth) {
            this.canvas.width = videoWidth;
            this.canvas.height = videoHeight;
        }
        
        // Draw frame
        this.ctx.drawImage(this.video, 0, 0);
        
        // SINGLE PASS - Direct scan only for maximum speed
        const imageData = this.ctx.getImageData(0, 0, videoWidth, videoHeight);
        const result = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'dontInvert' // No inversion for speed
        });
        
        if (result && result.data) {
            this.instantSuccess(result.data);
        }
    }
    
    instantSuccess(qrData) {
        // Ultra-short duplicate prevention
        const now = Date.now();
        if (qrData === this.lastScan && (now - this.lastScanTime) < this.duplicateTimeout) {
            return;
        }
        
        this.lastScan = qrData;
        this.lastScanTime = now;
        
        // Minimal feedback
        this.flashDetection();
        
        // Tiny haptic
        if (navigator.vibrate) {
            navigator.vibrate(30);
        }
        
        // Immediate callback
        if (this.onSuccess) {
            this.onSuccess(qrData);
        }
        
        // Continue scanning without pause in continuous mode
        if (!this.continuousMode) {
            setTimeout(() => {
                this.lastScan = ''; // Reset for next scan
            }, this.duplicateTimeout);
        }
    }
    
    flashDetection() {
        // Quick visual flash
        this.lensFrame.style.borderColor = '#34a853';
        setTimeout(() => {
            this.lensFrame.style.borderColor = '';
        }, 100);
        
        // Brief status update
        this.status.textContent = '✓ Detected';
        setTimeout(() => {
            this.status.textContent = 'Scanning...';
        }, 200);
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
window.GoogleLensScanner = GoogleLensScanner;