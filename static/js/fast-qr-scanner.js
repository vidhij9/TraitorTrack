/**
 * Fast QR Scanner - Optimized for Speed
 * ======================================
 * Minimal, blazing-fast QR scanner
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
        
        console.log('FastQR: Initializing');
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
        this.context = this.canvas.getContext('2d');
    }
    
    setupControls() {
        const torchBtn = document.getElementById('torch-btn');
        if (torchBtn) {
            torchBtn.addEventListener('click', () => this.toggleTorch());
        }
    }
    
    async startCamera() {
        try {
            // Simple camera constraints
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                audio: false
            };
            
            this.cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.cameraStream;
            
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play().then(resolve);
                };
            });
            
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
        
        let frameSkip = 0;
        
        const scan = () => {
            if (!this.isScanning) return;
            
            if (!this.isPaused && this.video.readyState === 4) {
                // Scan every 3rd frame for performance
                frameSkip++;
                if (frameSkip % 3 === 0) {
                    // Update canvas size only if needed
                    if (this.canvas.width !== this.video.videoWidth) {
                        this.canvas.width = this.video.videoWidth;
                        this.canvas.height = this.video.videoHeight;
                    }
                    
                    if (this.canvas.width > 0 && this.canvas.height > 0) {
                        this.context.drawImage(this.video, 0, 0);
                        
                        // Single fast scan
                        const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
                        const code = jsQR(imageData.data, imageData.width, imageData.height, {
                            inversionAttempts: 'dontInvert' // Fast mode
                        });
                        
                        if (code && code.data) {
                            this.handleSuccess(code.data);
                        }
                    }
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
        
        try {
            await track.applyConstraints({
                advanced: [{ torch: this.torchEnabled }]
            });
            if (torchBtn) torchBtn.classList.toggle('active', this.torchEnabled);
        } catch (e) {
            console.log('FastQR: Torch not supported');
        }
    }
    
    handleSuccess(qrText) {
        // Prevent duplicate scans
        const now = Date.now();
        if (qrText === this.lastScan && (now - this.lastScanTime) < 500) {
            return;
        }
        
        if (this.isPaused) return;
        
        console.log('FastQR: Success:', qrText);
        
        this.lastScan = qrText;
        this.lastScanTime = now;
        
        // Pause scanning
        this.pauseScanning();
        
        // Visual feedback
        const flash = document.getElementById('success-flash');
        if (flash) {
            flash.classList.add('show');
            setTimeout(() => flash.classList.remove('show'), 200);
        }
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(100);
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