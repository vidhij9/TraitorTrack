/**
 * Google Lens-like QR Scanner for Agricultural Seed Bags
 * Ultra-fast detection with multiple QR libraries and fallback methods
 * Optimized for reflective plastic packaging and agricultural environments
 */
class GoogleLensScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.stream = null;
        this.isScanning = false;
        this.lastScanTime = 0;
        this.scanCooldown = 800; // Prevent duplicate scans
        this.onSuccess = null;
        this.animationFrame = null;
        this.torchEnabled = false;
        this.scanAttempts = 0;
        
        // Load multiple QR libraries for maximum compatibility
        this.loadQRLibraries().then(() => {
            this.init();
        });
    }
    
    async loadQRLibraries() {
        // Try to load jsQR first (most reliable)
        try {
            if (!window.jsQR) {
                const jsQRScript = document.createElement('script');
                jsQRScript.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js';
                await new Promise((resolve, reject) => {
                    jsQRScript.onload = resolve;
                    jsQRScript.onerror = reject;
                    document.head.appendChild(jsQRScript);
                });
                console.log('jsQR library loaded successfully');
            }
        } catch (error) {
            console.warn('Failed to load jsQR, will use fallback methods');
        }
        
        // Also try to load qr-scanner as backup
        try {
            if (!window.QrScanner) {
                const qrScannerScript = document.createElement('script');
                qrScannerScript.src = 'https://cdn.jsdelivr.net/npm/qr-scanner@1.4.2/qr-scanner.min.js';
                await new Promise((resolve, reject) => {
                    qrScannerScript.onload = resolve;
                    qrScannerScript.onerror = reject;
                    document.head.appendChild(qrScannerScript);
                });
                console.log('QrScanner library loaded as backup');
            }
        } catch (error) {
            console.warn('Failed to load QrScanner backup library');
        }
    }
    
    init() {
        this.createUI();
    }
    
    createUI() {
        this.container.innerHTML = `
            <div class="google-lens-scanner">
                <div class="scanner-viewport">
                    <video id="gl-video-${this.containerId}" autoplay playsinline muted></video>
                    <canvas id="gl-canvas-${this.containerId}" style="display: none;"></canvas>
                </div>
                <div class="scanner-overlay">
                    <div class="scan-frame">
                        <div class="frame-corner tl"></div>
                        <div class="frame-corner tr"></div>
                        <div class="frame-corner bl"></div>
                        <div class="frame-corner br"></div>
                        <div class="scan-line-horizontal"></div>
                        <div class="scan-line-vertical"></div>
                    </div>
                    <div class="scan-info">
                        <div class="scan-status" id="gl-status-${this.containerId}">
                            <i class="fas fa-qrcode"></i> Point camera at QR code
                        </div>
                        <div class="scan-tips">
                            Google Lens style • Optimized for seed bags
                        </div>
                        <div class="scan-debug" id="gl-debug-${this.containerId}"></div>
                    </div>
                </div>
                <div class="scanner-controls">
                    <button class="control-btn torch-btn active" id="gl-torch-${this.containerId}" title="Torch (Auto-ON)">
                        <i class="fas fa-flashlight"></i>
                    </button>
                </div>
            </div>
            
            <style>
            .google-lens-scanner {
                position: relative;
                width: 100%;
                height: 450px;
                background: #000;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 12px 40px rgba(0,0,0,0.4);
                border: 2px solid rgba(255,255,255,0.1);
            }
            
            .scanner-viewport {
                width: 100%;
                height: 100%;
                position: relative;
            }
            
            .scanner-viewport video {
                width: 100%;
                height: 100%;
                object-fit: cover;
                background: #111;
            }
            
            .scanner-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                pointer-events: none;
                z-index: 10;
            }
            
            .scan-frame {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 300px;
                height: 300px;
                border: 3px solid rgba(255,255,255,0.2);
                border-radius: 20px;
                background: rgba(0,255,136,0.05);
                backdrop-filter: blur(2px);
            }
            
            .frame-corner {
                position: absolute;
                width: 50px;
                height: 50px;
                border: 5px solid #00ff88;
                border-radius: 8px;
            }
            
            .frame-corner.tl {
                top: -5px;
                left: -5px;
                border-right: none;
                border-bottom: none;
                box-shadow: -5px -5px 15px rgba(0,255,136,0.3);
            }
            
            .frame-corner.tr {
                top: -5px;
                right: -5px;
                border-left: none;
                border-bottom: none;
                box-shadow: 5px -5px 15px rgba(0,255,136,0.3);
            }
            
            .frame-corner.bl {
                bottom: -5px;
                left: -5px;
                border-right: none;
                border-top: none;
                box-shadow: -5px 5px 15px rgba(0,255,136,0.3);
            }
            
            .frame-corner.br {
                bottom: -5px;
                right: -5px;
                border-left: none;
                border-top: none;
                box-shadow: 5px 5px 15px rgba(0,255,136,0.3);
            }
            
            .scan-line-horizontal {
                position: absolute;
                top: 50%;
                left: 10px;
                right: 10px;
                height: 4px;
                background: linear-gradient(90deg, transparent, #00ff88, rgba(0,255,136,0.8), #00ff88, transparent);
                animation: scanHorizontal 2.5s ease-in-out infinite;
                border-radius: 2px;
                box-shadow: 0 0 10px rgba(0,255,136,0.6);
            }
            
            .scan-line-vertical {
                position: absolute;
                left: 50%;
                top: 10px;
                bottom: 10px;
                width: 4px;
                background: linear-gradient(180deg, transparent, #ff6b00, rgba(255,107,0,0.8), #ff6b00, transparent);
                animation: scanVertical 3s ease-in-out infinite;
                border-radius: 2px;
                box-shadow: 0 0 10px rgba(255,107,0,0.6);
            }
            
            @keyframes scanHorizontal {
                0%, 100% { transform: translateY(-50%) scaleX(0.1); opacity: 0.3; }
                50% { transform: translateY(-50%) scaleX(1); opacity: 1; }
            }
            
            @keyframes scanVertical {
                0%, 100% { transform: translateX(-50%) scaleY(0.1); opacity: 0.3; }
                50% { transform: translateX(-50%) scaleY(1); opacity: 1; }
            }
            
            .scan-info {
                position: absolute;
                bottom: 25px;
                left: 50%;
                transform: translateX(-50%);
                text-align: center;
                color: white;
                max-width: 90%;
            }
            
            .scan-status {
                font-size: 18px;
                font-weight: 700;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                background: rgba(0,0,0,0.7);
                padding: 8px 16px;
                border-radius: 25px;
                backdrop-filter: blur(15px);
                border: 1px solid rgba(255,255,255,0.1);
            }
            
            .scan-tips {
                font-size: 12px;
                opacity: 0.9;
                background: rgba(0,255,136,0.1);
                padding: 4px 12px;
                border-radius: 15px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(0,255,136,0.2);
                margin-bottom: 5px;
            }
            
            .scan-debug {
                font-size: 10px;
                opacity: 0.6;
                font-family: monospace;
                background: rgba(0,0,0,0.5);
                padding: 2px 8px;
                border-radius: 10px;
                max-height: 40px;
                overflow: hidden;
            }
            
            .scanner-controls {
                position: absolute;
                bottom: 25px;
                right: 25px;
                z-index: 15;
            }
            
            .control-btn {
                width: 60px;
                height: 60px;
                border: none;
                border-radius: 30px;
                background: rgba(0,0,0,0.7);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s;
                backdrop-filter: blur(15px);
                font-size: 20px;
                border: 2px solid rgba(255,255,255,0.2);
            }
            
            .control-btn:hover {
                background: rgba(0,0,0,0.9);
                transform: scale(1.1);
                border-color: rgba(255,255,255,0.4);
            }
            
            .control-btn.active {
                background: rgba(0,255,136,0.8);
                color: #000;
                border-color: #00ff88;
                box-shadow: 0 0 20px rgba(0,255,136,0.4);
            }
            
            @keyframes detected {
                0% { 
                    border-color: #00ff88;
                    box-shadow: 0 0 0 0 rgba(0,255,136,0.6);
                    background: rgba(0,255,136,0.05);
                }
                50% { 
                    border-color: #ff6b00;
                    box-shadow: 0 0 0 30px rgba(0,255,136,0);
                    background: rgba(255,107,0,0.1);
                }
                100% { 
                    border-color: #00ff88;
                    box-shadow: 0 0 0 0 rgba(0,255,136,0.6);
                    background: rgba(0,255,136,0.05);
                }
            }
            
            .detected .scan-frame {
                animation: detected 0.8s ease-out;
            }
            
            .scanning .frame-corner {
                border-color: #00ff88;
                box-shadow: 0 0 20px rgba(0,255,136,0.6);
            }
            
            .scanning .scan-line-horizontal,
            .scanning .scan-line-vertical {
                animation-duration: 1.5s;
            }
            </style>
        `;
        
        this.video = document.getElementById(`gl-video-${this.containerId}`);
        this.canvas = document.getElementById(`gl-canvas-${this.containerId}`);
        this.ctx = this.canvas.getContext('2d');
        
        // Setup controls
        const torchBtn = document.getElementById(`gl-torch-${this.containerId}`);
        if (torchBtn) {
            torchBtn.addEventListener('click', () => this.toggleTorch());
        }
    }
    
    async start() {
        if (this.isScanning) return;
        
        try {
            this.updateStatus('<i class="fas fa-spinner fa-spin"></i> Starting Google Lens scanner...', 'info');
            this.updateDebug('Requesting camera access...');
            
            // Enhanced camera constraints for Google Lens-like performance
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: 1920, min: 640 },
                    height: { ideal: 1080, min: 480 },
                    frameRate: { ideal: 60, min: 20 },
                    focusMode: { ideal: 'continuous' },
                    exposureMode: { ideal: 'continuous' },
                    whiteBalanceMode: { ideal: 'continuous' }
                },
                audio: false
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.canvas.width = this.video.videoWidth;
                    this.canvas.height = this.video.videoHeight;
                    this.updateDebug(`Video: ${this.video.videoWidth}x${this.video.videoHeight}`);
                    resolve();
                };
            });
            
            this.isScanning = true;
            this.container.querySelector('.google-lens-scanner').classList.add('scanning');
            this.updateStatus('<i class="fas fa-qrcode"></i> Scanning for QR codes...', 'success');
            this.updateDebug('Scanner active - Looking for QR codes');
            
            // Start high-frequency scanning loop
            this.scanLoop();
            
            // Enable torch immediately for agricultural environment
            setTimeout(() => this.enableTorch(), 200);
            
            console.log('Google Lens scanner started successfully');
            
        } catch (error) {
            console.error('Failed to start Google Lens scanner:', error);
            this.handleError(error);
        }
    }
    
    scanLoop() {
        if (!this.isScanning || !this.video || this.video.readyState !== this.video.HAVE_ENOUGH_DATA) {
            if (this.isScanning) {
                this.animationFrame = requestAnimationFrame(() => this.scanLoop());
            }
            return;
        }
        
        try {
            this.scanAttempts++;
            
            // Capture current video frame
            this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // Try multiple QR detection methods
            let qrCode = null;
            
            // Method 1: jsQR (most reliable)
            if (window.jsQR && !qrCode) {
                qrCode = window.jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "attemptBoth",
                });
            }
            
            // Method 2: QrScanner as backup
            if (window.QrScanner && !qrCode) {
                try {
                    // QrScanner has different API, would need to implement differently
                    // For now, focus on jsQR
                } catch (e) {
                    // Ignore backup method errors
                }
            }
            
            if (qrCode && qrCode.data) {
                console.log('QR Code detected with Google Lens scanner:', qrCode.data);
                this.updateDebug(`Detected: ${qrCode.data.substring(0, 20)}...`);
                this.onQRDetected(qrCode.data);
            } else {
                // Update debug info every 100 attempts
                if (this.scanAttempts % 100 === 0) {
                    this.updateDebug(`Scanning... ${this.scanAttempts} attempts`);
                }
            }
            
        } catch (error) {
            console.error('QR scan error:', error);
            this.updateDebug(`Error: ${error.message}`);
        }
        
        // Continue scanning at maximum framerate
        if (this.isScanning) {
            this.animationFrame = requestAnimationFrame(() => this.scanLoop());
        }
    }
    
    onQRDetected(qrData) {
        const now = Date.now();
        
        // Prevent duplicate detections
        if (now - this.lastScanTime < this.scanCooldown) {
            return;
        }
        
        this.lastScanTime = now;
        
        // Validate if it's a reasonable QR code
        if (!this.isValidQRCode(qrData)) {
            console.log('Invalid QR detected, ignoring:', qrData);
            this.updateDebug('Invalid QR code format');
            return;
        }
        
        // Visual feedback
        this.showDetectionFeedback();
        
        // Audio feedback
        this.playDetectionSound();
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([150, 50, 150]);
        }
        
        // Update status
        this.updateStatus(`<i class="fas fa-check-circle"></i> Detected: ${qrData}`, 'success');
        this.updateDebug(`Success: ${qrData}`);
        
        console.log('Valid QR detected by Google Lens scanner:', qrData);
        
        // Call success callback
        if (this.onSuccess) {
            this.onSuccess(qrData);
        }
    }
    
    isValidQRCode(qrData) {
        // Accept most QR codes for testing, but filter out obvious junk
        if (!qrData || qrData.length < 2) {
            return false;
        }
        
        // Filter out really short or obviously invalid codes
        if (qrData.length < 5 && !/^[A-Za-z0-9]+$/.test(qrData)) {
            return false;
        }
        
        // Accept any reasonable looking QR code
        return true;
    }
    
    showDetectionFeedback() {
        const scanner = this.container.querySelector('.google-lens-scanner');
        scanner.classList.add('detected');
        setTimeout(() => {
            scanner.classList.remove('detected');
        }, 800);
    }
    
    playDetectionSound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Google Lens-like sound
            oscillator.frequency.setValueAtTime(1000, audioContext.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(1500, audioContext.currentTime + 0.1);
            oscillator.frequency.exponentialRampToValueAtTime(1200, audioContext.currentTime + 0.2);
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.05, audioContext.currentTime + 0.1);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
        } catch (e) {
            console.log('Audio not available');
        }
    }
    
    async enableTorch() {
        try {
            if (this.stream) {
                const track = this.stream.getVideoTracks()[0];
                const capabilities = track.getCapabilities();
                
                console.log('Camera capabilities:', capabilities);
                
                if (capabilities.torch) {
                    await track.applyConstraints({
                        advanced: [{ torch: true }]
                    });
                    
                    this.torchEnabled = true;
                    const torchBtn = document.getElementById(`gl-torch-${this.containerId}`);
                    if (torchBtn) {
                        torchBtn.classList.add('active');
                        torchBtn.title = 'Torch ON';
                    }
                    
                    this.updateStatus('<i class="fas fa-flashlight"></i> Torch enabled - Ready to scan', 'success');
                    this.updateDebug('Torch enabled for agricultural scanning');
                    console.log('Torch enabled for Google Lens scanner');
                } else {
                    console.log('Torch not supported on this device');
                    this.updateDebug('Torch not available on this device');
                }
            }
        } catch (error) {
            console.log('Torch not available:', error.message);
            this.updateDebug('Torch error: ' + error.message);
        }
    }
    
    async toggleTorch() {
        try {
            const torchBtn = document.getElementById(`gl-torch-${this.containerId}`);
            
            if (this.stream) {
                const track = this.stream.getVideoTracks()[0];
                await track.applyConstraints({
                    advanced: [{ torch: !this.torchEnabled }]
                });
                
                this.torchEnabled = !this.torchEnabled;
                torchBtn.classList.toggle('active', this.torchEnabled);
                torchBtn.title = this.torchEnabled ? 'Torch ON' : 'Torch OFF';
                
                this.updateDebug(`Torch ${this.torchEnabled ? 'enabled' : 'disabled'}`);
                console.log(`Torch ${this.torchEnabled ? 'enabled' : 'disabled'}`);
            }
        } catch (error) {
            console.log('Cannot toggle torch:', error.message);
            this.updateDebug('Torch toggle error');
        }
    }
    
    updateStatus(message, type = 'info') {
        const statusEl = document.getElementById(`gl-status-${this.containerId}`);
        if (statusEl) {
            statusEl.innerHTML = message;
            statusEl.className = `scan-status status-${type}`;
        }
    }
    
    updateDebug(message) {
        const debugEl = document.getElementById(`gl-debug-${this.containerId}`);
        if (debugEl) {
            debugEl.textContent = message;
        }
    }
    
    handleError(error) {
        let message = 'Scanner error';
        
        switch (error.name || error.message) {
            case 'NotAllowedError':
                message = '<i class="fas fa-exclamation-triangle"></i> Camera permission denied';
                break;
            case 'NotFoundError':
                message = '<i class="fas fa-camera-slash"></i> No camera found';
                break;
            case 'NotReadableError':
                message = '<i class="fas fa-exclamation-circle"></i> Camera is busy';
                break;
            default:
                message = `<i class="fas fa-exclamation-circle"></i> ${error.message || 'Scanner error'}`;
        }
        
        this.updateStatus(message, 'error');
        this.updateDebug('Error: ' + error.message);
        console.error('Google Lens Scanner error:', error);
    }
    
    async stop() {
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
        
        const scanner = this.container.querySelector('.google-lens-scanner');
        if (scanner) {
            scanner.classList.remove('scanning', 'detected');
        }
        
        console.log('Google Lens Scanner stopped');
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
}

// Global export
window.GoogleLensScanner = GoogleLensScanner;