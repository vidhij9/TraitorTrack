/**
 * Fast QR Scanner - Ultra Fast Google Lens Speed
 * ===============================================
 * Optimized for maximum scanning performance
 */

class FastQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.isScanning = false;
        this.isPaused = false;
        this.onSuccess = null;
        this.cameraStream = null;
        this.lastScan = '';
        this.lastScanTime = 0;
        this.torchEnabled = false;
        
        // Ultra-fast optimizations
        this.targetWidth = 640;  // Lower resolution for speed
        this.targetHeight = 480;
        this.scanRegion = 0.6;   // Focus on center 60%
        this.frameCount = 0;
        this.fpsFrames = [];
        
        console.log('FastQR: Initializing Ultra-Fast Mode');
        this.init();
    }
    
    async init() {
        this.setupUI();
        this.setupElements();
        this.setupControls();
        await this.startCamera();
    }
    
    setupUI() {
        this.container.innerHTML = `
            <div class="fast-qr-scanner">
                <video id="${this.containerId}-video" autoplay playsinline muted></video>
                <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
                
                <div class="scan-overlay">
                    <div class="scan-box">
                        <div class="corner tl"></div>
                        <div class="corner tr"></div>
                        <div class="corner bl"></div>
                        <div class="corner br"></div>
                    </div>
                    <div class="scan-text">Position QR code in frame</div>
                </div>
                
                <div class="controls">
                    <button id="torch-btn" class="control-btn" title="Flashlight">💡</button>
                </div>
                
                <div class="success-flash" id="success-flash"></div>
            </div>
            
            <style>
                .fast-qr-scanner {
                    position: relative;
                    width: 100%;
                    height: 400px;
                    border-radius: 8px;
                    overflow: hidden;
                    background: #000;
                }
                
                #${this.containerId}-video {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }
                
                .scan-overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    pointer-events: none;
                }
                
                .scan-box {
                    position: relative;
                    width: 200px;
                    height: 200px;
                    margin-bottom: 20px;
                }
                
                .corner {
                    position: absolute;
                    width: 20px;
                    height: 20px;
                    border: 2px solid #00ff00;
                }
                
                .corner.tl {
                    top: 0; left: 0;
                    border-right: none;
                    border-bottom: none;
                }
                
                .corner.tr {
                    top: 0; right: 0;
                    border-left: none;
                    border-bottom: none;
                }
                
                .corner.bl {
                    bottom: 0; left: 0;
                    border-right: none;
                    border-top: none;
                }
                
                .corner.br {
                    bottom: 0; right: 0;
                    border-left: none;
                    border-top: none;
                }
                
                .scan-text {
                    color: white;
                    font-size: 14px;
                    text-shadow: 0 1px 3px rgba(0,0,0,0.7);
                }
                
                .controls {
                    position: absolute;
                    bottom: 15px;
                    left: 50%;
                    transform: translateX(-50%);
                    pointer-events: auto;
                }
                
                .control-btn {
                    width: 45px;
                    height: 45px;
                    border-radius: 50%;
                    background: rgba(255,255,255,0.9);
                    border: none;
                    font-size: 20px;
                    cursor: pointer;
                }
                
                .control-btn.active {
                    background: #ffd700;
                }
                
                .success-flash {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 255, 0, 0.3);
                    opacity: 0;
                    pointer-events: none;
                    transition: opacity 0.2s ease;
                }
                
                .success-flash.show {
                    opacity: 1;
                }
            </style>
        `;
    }
    
    setupElements() {
        this.video = document.getElementById(`${this.containerId}-video`);
        this.canvas = document.getElementById(`${this.containerId}-canvas`);
        // Optimize context for performance
        this.context = this.canvas.getContext('2d', {
            willReadFrequently: true,
            alpha: false,
            desynchronized: true
        });
    }
    
    setupControls() {
        const torchBtn = document.getElementById('torch-btn');
        if (torchBtn) {
            torchBtn.addEventListener('click', () => this.toggleTorch());
        }
    }
    
    async startCamera() {
        try {
            // Optimized constraints for ultra-fast scanning
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: this.targetWidth },
                    height: { ideal: this.targetHeight },
                    frameRate: { ideal: 60, min: 30 }, // Higher FPS
                    resizeMode: 'crop-and-scale',
                    aspectRatio: 4/3
                },
                audio: false
            };
            
            this.cameraStream = await navigator.mediaDevices.getUserMedia(constraints)
                .catch(() => {
                    // Fallback to simpler constraints
                    return navigator.mediaDevices.getUserMedia({ 
                        video: { facingMode: 'environment' }, 
                        audio: false 
                    });
                });
            this.video.srcObject = this.cameraStream;
            
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play().then(resolve);
                };
            });
            
            // Apply performance optimizations
            const track = this.cameraStream.getVideoTracks()[0];
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
                    console.log('FastQR: Advanced constraints not supported');
                }
            }
            
            this.isScanning = true;
            this.startScanning();
            this.showStatus('Camera active! Point at QR code', 'success');
            
        } catch (error) {
            console.error('FastQR: Camera failed:', error);
            this.showStatus('Camera error. Please check permissions.', 'error');
        }
    }
    
    startScanning() {
        if (typeof jsQR === 'undefined') {
            console.error('FastQR: jsQR library not loaded');
            return;
        }
        
        let lastFrameTime = performance.now();
        
        const scan = () => {
            if (!this.isScanning) return;
            
            // FPS tracking
            const currentTime = performance.now();
            const deltaTime = currentTime - lastFrameTime;
            lastFrameTime = currentTime;
            
            if (this.fpsFrames.length < 30) {
                this.fpsFrames.push(1000 / deltaTime);
            } else {
                this.fpsFrames.shift();
                this.fpsFrames.push(1000 / deltaTime);
            }
            
            if (!this.isPaused && this.video.readyState === 4) {
                // Scan EVERY frame for maximum speed - no skipping!
                // Use fixed canvas size for consistent performance
                if (this.canvas.width !== this.targetWidth) {
                    this.canvas.width = this.targetWidth;
                    this.canvas.height = this.targetHeight;
                }
                
                if (this.canvas.width > 0 && this.canvas.height > 0) {
                    // Draw at lower resolution for speed
                    this.context.drawImage(this.video, 0, 0, this.targetWidth, this.targetHeight);
                    
                    // Get center region for faster processing
                    const regionSize = Math.floor(this.targetWidth * this.scanRegion);
                    const offsetX = Math.floor((this.targetWidth - regionSize) / 2);
                    const offsetY = Math.floor((this.targetHeight - regionSize) / 2);
                    
                    const imageData = this.context.getImageData(
                        offsetX, offsetY, 
                        regionSize, regionSize
                    );
                    
                    // Ultra-fast single scan - no enhancements, no retries
                    const code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: 'dontInvert' // Fastest option
                    });
                    
                    if (code && code.data) {
                        this.handleSuccess(code.data);
                    }
                    
                    this.frameCount++;
                }
            }
            
            requestAnimationFrame(scan);
        };
        
        scan();
    }
    
    async toggleTorch() {
        const track = this.cameraStream?.getVideoTracks()[0];
        if (!track) return;
        
        const torchBtn = document.getElementById('torch-btn');
        this.torchEnabled = !this.torchEnabled;
        
        // Try multiple methods for universal torch support
        try {
            // Method 1: Standard constraints
            await track.applyConstraints({
                advanced: [{ torch: this.torchEnabled }]
            });
            if (torchBtn) torchBtn.classList.toggle('active', this.torchEnabled);
            console.log('FastQR: Torch toggled via advanced constraints');
        } catch (e1) {
            try {
                // Method 2: Direct constraint
                await track.applyConstraints({ torch: this.torchEnabled });
                if (torchBtn) torchBtn.classList.toggle('active', this.torchEnabled);
                console.log('FastQR: Torch toggled via direct constraint');
            } catch (e2) {
                try {
                    // Method 3: ImageCapture API for older devices
                    const imageCapture = new ImageCapture(track);
                    await imageCapture.setOptions({
                        fillLightMode: this.torchEnabled ? 'flash' : 'off'
                    });
                    if (torchBtn) torchBtn.classList.toggle('active', this.torchEnabled);
                    console.log('FastQR: Torch toggled via ImageCapture');
                } catch (e3) {
                    console.log('FastQR: Torch not supported on this device');
                    // Show user message
                    this.showStatus('Flashlight not available on this device', 'warning');
                }
            }
        }
    }
    
    handleSuccess(qrText) {
        // Prevent duplicate scans (shorter delay for faster response)
        const now = Date.now();
        if (qrText === this.lastScan && (now - this.lastScanTime) < 200) {
            return;
        }
        
        if (this.isPaused) return;
        
        console.log('FastQR: Success:', qrText);
        
        this.lastScan = qrText;
        this.lastScanTime = now;
        
        // Don't pause for continuous scanning
        // this.pauseScanning();
        
        // Visual feedback
        const flash = document.getElementById('success-flash');
        if (flash) {
            flash.classList.add('show');
            setTimeout(() => flash.classList.remove('show'), 200);
        }
        
        // Shorter haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
        
        if (this.onSuccess) {
            this.onSuccess(qrText);
        }
    }
    
    showStatus(message, type = 'info') {
        const scanText = this.container.querySelector('.scan-text');
        if (scanText) {
            scanText.textContent = message;
        }
        
        // Also update parent container if exists
        const resultContainer = document.getElementById('result-container');
        if (resultContainer) {
            resultContainer.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'}`;
            resultContainer.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>${message}`;
            resultContainer.style.display = 'block';
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
    
    pauseScanning() {
        this.isPaused = true;
        console.log('FastQR: Paused');
    }
    
    resumeScanning() {
        this.isPaused = false;
        console.log('FastQR: Resumed');
    }
    
    // Simple image enhancement for damaged codes
    enhanceImage(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const len = data.length;
        
        // Apply contrast and brightness adjustment
        for (let i = 0; i < len; i += 4) {
            // Convert to grayscale for better QR detection
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            
            // Apply contrast (1.5x) and brightness (+10)
            let enhanced = (gray - 128) * 1.5 + 128 + 10;
            
            // Clamp values
            enhanced = Math.max(0, Math.min(255, enhanced));
            
            // Set all channels to enhanced grayscale
            data[i] = data[i + 1] = data[i + 2] = enhanced;
        }
        
        return { data, width: imageData.width, height: imageData.height };
    }
    
    async stop() {
        this.isScanning = false;
        this.isPaused = false;
        
        if (this.cameraStream) {
            this.cameraStream.getTracks().forEach(track => track.stop());
            this.cameraStream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
        
        console.log('FastQR: Stopped');
    }
}

// Make LiveQRScanner use the fast implementation
class LiveQRScanner extends FastQRScanner {
    constructor(containerId) {
        super(containerId);
    }
}

// Global availability
window.FastQRScanner = FastQRScanner;
window.LiveQRScanner = LiveQRScanner;