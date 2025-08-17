/**
 * Fast QR Code Scanner Implementation
 * Optimized for agricultural bag scanning with instant detection
 */

class FastQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.stream = null;
        this.isScanning = false;
        this.lastScanTime = 0;
        this.scanCooldown = 500; // Prevent duplicate scans
        this.onSuccess = null;
        this.animationFrame = null;
        this.scannerWorking = false;
        
        // Load jsQR library dynamically
        this.loadJsQR().then(() => {
            this.init();
        });
    }
    
    async loadJsQR() {
        if (!window.jsQR) {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js';
                script.onload = () => {
                    console.log('jsQR library loaded successfully');
                    resolve();
                };
                script.onerror = () => {
                    console.error('Failed to load jsQR library');
                    reject(new Error('Failed to load QR scanning library'));
                };
                document.head.appendChild(script);
            });
        }
    }
    
    init() {
        this.createUI();
        this.setupEventHandlers();
    }
    
    createUI() {
        this.container.innerHTML = `
            <div class="qr-scanner-container">
                <div class="scanner-viewport">
                    <video id="video-${this.containerId}" autoplay playsinline muted></video>
                    <canvas id="canvas-${this.containerId}" style="display: none;"></canvas>
                </div>
                <div class="scanner-overlay">
                    <div class="scan-frame">
                        <div class="corner-frame top-left"></div>
                        <div class="corner-frame top-right"></div>
                        <div class="corner-frame bottom-left"></div>
                        <div class="corner-frame bottom-right"></div>
                        <div class="scan-line"></div>
                    </div>
                    <div class="scan-instructions">
                        <div class="scan-status" id="scan-status-${this.containerId}">
                            <i class="fas fa-camera"></i> Initializing camera...
                        </div>
                    </div>
                </div>
                <div class="scanner-controls">
                    <button class="control-btn" id="torch-btn-${this.containerId}" title="Toggle Flashlight">
                        <i class="fas fa-lightbulb"></i>
                    </button>
                </div>
            </div>
            
            <style>
            .qr-scanner-container {
                position: relative;
                width: 100%;
                height: 400px;
                background: #000;
                border-radius: 12px;
                overflow: hidden;
            }
            
            .scanner-viewport {
                position: relative;
                width: 100%;
                height: 100%;
            }
            
            .scanner-viewport video {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            
            .scanner-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                pointer-events: none;
            }
            
            .scan-frame {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 250px;
                height: 250px;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            
            .corner-frame {
                position: absolute;
                width: 30px;
                height: 30px;
                border: 3px solid #00ff88;
            }
            
            .corner-frame.top-left {
                top: 0;
                left: 0;
                border-right: none;
                border-bottom: none;
            }
            
            .corner-frame.top-right {
                top: 0;
                right: 0;
                border-left: none;
                border-bottom: none;
            }
            
            .corner-frame.bottom-left {
                bottom: 0;
                left: 0;
                border-right: none;
                border-top: none;
            }
            
            .corner-frame.bottom-right {
                bottom: 0;
                right: 0;
                border-left: none;
                border-top: none;
            }
            
            .scan-line {
                position: absolute;
                width: 100%;
                height: 2px;
                background: linear-gradient(90deg, transparent, #00ff88, transparent);
                animation: scan 2s linear infinite;
            }
            
            @keyframes scan {
                0% { top: 0; }
                100% { top: 100%; }
            }
            
            .scan-instructions {
                position: absolute;
                bottom: 20px;
                left: 0;
                right: 0;
                text-align: center;
                color: white;
            }
            
            .scan-status {
                background: rgba(0, 0, 0, 0.7);
                display: inline-block;
                padding: 8px 20px;
                border-radius: 20px;
                font-size: 14px;
            }
            
            .scanner-controls {
                position: absolute;
                bottom: 20px;
                right: 20px;
            }
            
            .control-btn {
                width: 44px;
                height: 44px;
                border: none;
                border-radius: 22px;
                background: rgba(255, 255, 255, 0.9);
                color: #333;
                cursor: pointer;
                transition: all 0.3s;
            }
            
            .control-btn:hover {
                background: white;
                transform: scale(1.1);
            }
            
            .control-btn.active {
                background: #ffc107;
                color: white;
            }
            
            .scan-success-flash {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 255, 100, 0.3);
                animation: flash 0.3s ease-out;
                pointer-events: none;
            }
            
            @keyframes flash {
                0% { opacity: 0; }
                50% { opacity: 1; }
                100% { opacity: 0; }
            }
            </style>
        `;
        
        this.video = document.getElementById(`video-${this.containerId}`);
        this.canvas = document.getElementById(`canvas-${this.containerId}`);
        this.ctx = this.canvas.getContext('2d');
    }
    
    setupEventHandlers() {
        const torchBtn = document.getElementById(`torch-btn-${this.containerId}`);
        if (torchBtn) {
            torchBtn.addEventListener('click', () => this.toggleTorch());
        }
    }
    
    async start() {
        try {
            this.updateStatus('Requesting camera access...', 'info');
            
            // Request camera with optimal settings for QR scanning
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    frameRate: { ideal: 30 }
                }
            };
            
            try {
                this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (error) {
                console.warn('Failed with ideal constraints, trying basic...');
                // Fallback to basic constraints
                this.stream = await navigator.mediaDevices.getUserMedia({ video: true });
            }
            
            this.video.srcObject = this.stream;
            
            // Wait for video to be ready
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play();
                    resolve();
                };
            });
            
            // Set canvas dimensions to match video
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            
            this.isScanning = true;
            this.updateStatus('Point camera at QR code', 'success');
            
            // Start scanning
            this.scan();
            
        } catch (error) {
            console.error('Camera start error:', error);
            this.updateStatus('Camera access denied', 'error');
            throw error;
        }
    }
    
    scan() {
        if (!this.isScanning) return;
        
        // Don't scan too frequently if we're already processing
        if (this.scannerWorking) {
            this.animationFrame = requestAnimationFrame(() => this.scan());
            return;
        }
        
        try {
            // Draw current video frame to canvas
            this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            
            // Get image data
            const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // Use jsQR to detect QR code
            if (window.jsQR) {
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "dontInvert"
                });
                
                if (code && code.data) {
                    // QR code detected!
                    const now = Date.now();
                    if (now - this.lastScanTime > this.scanCooldown) {
                        this.lastScanTime = now;
                        this.handleSuccess(code.data);
                    }
                }
            }
            
        } catch (error) {
            console.error('Scan error:', error);
        }
        
        // Continue scanning
        this.animationFrame = requestAnimationFrame(() => this.scan());
    }
    
    handleSuccess(qrCode) {
        console.log('QR Code detected:', qrCode);
        
        // Visual feedback
        this.showSuccessFlash();
        this.updateStatus('QR Code detected!', 'success');
        
        // Vibrate if available
        if (navigator.vibrate) {
            navigator.vibrate(200);
        }
        
        // Call success callback
        if (this.onSuccess) {
            this.scannerWorking = true;
            
            // Call the callback and handle the result
            Promise.resolve(this.onSuccess(qrCode)).then(() => {
                this.scannerWorking = false;
                this.updateStatus('Ready to scan next', 'success');
            }).catch((error) => {
                console.error('Callback error:', error);
                this.scannerWorking = false;
                this.updateStatus('Error processing QR code', 'error');
            });
        }
    }
    
    showSuccessFlash() {
        const flash = document.createElement('div');
        flash.className = 'scan-success-flash';
        this.container.querySelector('.scanner-viewport').appendChild(flash);
        setTimeout(() => flash.remove(), 300);
    }
    
    updateStatus(message, type) {
        const statusEl = document.getElementById(`scan-status-${this.containerId}`);
        if (statusEl) {
            let icon = 'fas fa-qrcode';
            let color = '';
            
            switch(type) {
                case 'info':
                    icon = 'fas fa-info-circle';
                    color = '#17a2b8';
                    break;
                case 'success':
                    icon = 'fas fa-check-circle';
                    color = '#28a745';
                    break;
                case 'error':
                    icon = 'fas fa-exclamation-circle';
                    color = '#dc3545';
                    break;
            }
            
            statusEl.innerHTML = `<i class="${icon}" style="color: ${color};"></i> ${message}`;
        }
    }
    
    async toggleTorch() {
        if (!this.stream) return;
        
        const track = this.stream.getVideoTracks()[0];
        const capabilities = track.getCapabilities();
        
        if (!capabilities.torch) {
            console.log('Torch not supported on this device');
            return;
        }
        
        const torchBtn = document.getElementById(`torch-btn-${this.containerId}`);
        const settings = track.getSettings();
        const torchOn = !settings.torch;
        
        try {
            await track.applyConstraints({
                advanced: [{ torch: torchOn }]
            });
            
            if (torchBtn) {
                torchBtn.classList.toggle('active', torchOn);
            }
        } catch (error) {
            console.error('Failed to toggle torch:', error);
        }
    }
    
    stop() {
        this.isScanning = false;
        
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
        
        this.updateStatus('Scanner stopped', 'info');
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
}

// Global export
window.FastQRScanner = FastQRScanner;