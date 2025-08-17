/**
 * Native QR Scanner - Self-contained, no external dependencies
 * Uses browser's native barcode detection API with jsQR fallback
 */

class NativeQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.stream = null;
        this.isScanning = false;
        this.lastScanTime = 0;
        this.scanCooldown = 1000; // 1 second cooldown
        this.onSuccess = null;
        this.scanInterval = null;
        this.jsQRLoaded = false;
        
        this.init();
    }
    
    init() {
        this.createUI();
        this.loadJsQR();
    }
    
    createUI() {
        this.container.innerHTML = `
            <div class="native-scanner-container">
                <video id="video-${this.containerId}" autoplay muted playsinline></video>
                <canvas id="canvas-${this.containerId}" style="display: none;"></canvas>
                
                <div class="scanner-overlay">
                    <div class="scan-frame">
                        <div class="corner tl"></div>
                        <div class="corner tr"></div>
                        <div class="corner bl"></div>
                        <div class="corner br"></div>
                        <div class="scan-line"></div>
                    </div>
                    
                    <div class="status-bar">
                        <span id="status-${this.containerId}">Initializing...</span>
                    </div>
                </div>
                
                <div class="controls">
                    <button id="torch-${this.containerId}" class="torch-btn" style="display: none;">
                        <i class="fas fa-flashlight"></i> Torch
                    </button>
                </div>
            </div>
            
            <style>
            .native-scanner-container {
                position: relative;
                width: 100%;
                max-width: 500px;
                margin: 0 auto;
                background: #000;
                border-radius: 12px;
                overflow: hidden;
            }
            
            #video-${this.containerId} {
                width: 100%;
                height: 400px;
                object-fit: cover;
                display: block;
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
            }
            
            .corner {
                position: absolute;
                width: 30px;
                height: 30px;
                border: 3px solid #00ff41;
                border-radius: 4px;
            }
            
            .corner.tl {
                top: 0;
                left: 0;
                border-right: none;
                border-bottom: none;
            }
            
            .corner.tr {
                top: 0;
                right: 0;
                border-left: none;
                border-bottom: none;
            }
            
            .corner.bl {
                bottom: 0;
                left: 0;
                border-right: none;
                border-top: none;
            }
            
            .corner.br {
                bottom: 0;
                right: 0;
                border-left: none;
                border-top: none;
            }
            
            .scan-line {
                position: absolute;
                width: 100%;
                height: 2px;
                background: linear-gradient(90deg, transparent, #00ff41, transparent);
                animation: scanning 2s linear infinite;
                box-shadow: 0 0 10px #00ff41;
            }
            
            @keyframes scanning {
                0% { top: 0; opacity: 0; }
                10% { opacity: 1; }
                90% { opacity: 1; }
                100% { top: 100%; opacity: 0; }
            }
            
            .status-bar {
                position: absolute;
                bottom: 20px;
                left: 20px;
                right: 20px;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 10px;
                border-radius: 8px;
                text-align: center;
                font-size: 14px;
                font-weight: 500;
            }
            
            .controls {
                position: absolute;
                top: 20px;
                right: 20px;
                pointer-events: auto;
            }
            
            .torch-btn {
                background: rgba(0, 0, 0, 0.6);
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 25px;
                font-size: 12px;
                cursor: pointer;
                transition: background 0.3s;
            }
            
            .torch-btn:hover {
                background: rgba(0, 0, 0, 0.8);
            }
            
            .torch-btn.active {
                background: #007bff;
            }
            
            .scan-success {
                animation: success-flash 0.5s ease;
            }
            
            @keyframes success-flash {
                0%, 100% { background: rgba(0, 0, 0, 0.8); }
                50% { background: rgba(0, 255, 65, 0.3); }
            }
            </style>
        `;
        
        this.video = document.getElementById(`video-${this.containerId}`);
        this.canvas = document.getElementById(`canvas-${this.containerId}`);
        this.context = this.canvas.getContext('2d');
        
        // Setup torch button
        const torchBtn = document.getElementById(`torch-${this.containerId}`);
        torchBtn.addEventListener('click', () => this.toggleTorch());
    }
    
    loadJsQR() {
        // Check if jsQR is already loaded
        if (typeof jsQR !== 'undefined') {
            this.jsQRLoaded = true;
            console.log('jsQR already loaded');
            return;
        }
        
        // Load jsQR from CDN as fallback
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js';
        script.onload = () => {
            this.jsQRLoaded = true;
            console.log('jsQR loaded successfully');
        };
        script.onerror = () => {
            console.warn('jsQR failed to load, will use native detection only');
            this.jsQRLoaded = false;
        };
        document.head.appendChild(script);
    }
    
    async start() {
        try {
            this.updateStatus('Starting camera...');
            
            // Request camera access
            const constraints = {
                video: {
                    facingMode: 'environment', // Prefer rear camera
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            
            // Wait for video to load
            await new Promise((resolve) => {
                this.video.onloadedmetadata = resolve;
            });
            
            // Setup canvas dimensions
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            
            // Show torch button if supported
            this.setupTorch();
            
            // Start scanning
            this.isScanning = true;
            this.startScanning();
            
            this.updateStatus('Scanning - Point at QR code');
            console.log('Scanner started successfully');
            
        } catch (error) {
            console.error('Failed to start scanner:', error);
            this.updateStatus('Camera access denied');
            throw error;
        }
    }
    
    async setupTorch() {
        try {
            const track = this.stream.getVideoTracks()[0];
            const capabilities = track.getCapabilities();
            
            if (capabilities.torch) {
                document.getElementById(`torch-${this.containerId}`).style.display = 'block';
                this.torchSupported = true;
            }
        } catch (error) {
            console.log('Torch not supported');
        }
    }
    
    async toggleTorch() {
        if (!this.torchSupported) return;
        
        try {
            const track = this.stream.getVideoTracks()[0];
            const torchBtn = document.getElementById(`torch-${this.containerId}`);
            const isOn = torchBtn.classList.contains('active');
            
            await track.applyConstraints({
                advanced: [{ torch: !isOn }]
            });
            
            torchBtn.classList.toggle('active');
        } catch (error) {
            console.error('Failed to toggle torch:', error);
        }
    }
    
    startScanning() {
        // Try native BarcodeDetector first
        if ('BarcodeDetector' in window) {
            this.startNativeDetection();
        } else {
            this.startJsQRDetection();
        }
    }
    
    async startNativeDetection() {
        try {
            const barcodeDetector = new BarcodeDetector({ formats: ['qr_code'] });
            console.log('Using native BarcodeDetector');
            
            const scanFrame = () => {
                if (!this.isScanning) return;
                
                barcodeDetector.detect(this.video)
                    .then(barcodes => {
                        if (barcodes.length > 0) {
                            const qrCode = barcodes[0].rawValue;
                            this.handleDetection(qrCode);
                        }
                        
                        if (this.isScanning) {
                            requestAnimationFrame(scanFrame);
                        }
                    })
                    .catch(() => {
                        // Fallback to jsQR if native detection fails
                        this.startJsQRDetection();
                    });
            };
            
            scanFrame();
            
        } catch (error) {
            console.log('Native detection failed, using jsQR');
            this.startJsQRDetection();
        }
    }
    
    startJsQRDetection() {
        console.log('Using jsQR detection');
        
        const scanFrame = () => {
            if (!this.isScanning) return;
            
            if (this.jsQRLoaded && typeof jsQR !== 'undefined') {
                // Capture frame
                this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
                
                // Scan for QR code
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "dontInvert"
                });
                
                if (code) {
                    this.handleDetection(code.data);
                }
            }
            
            if (this.isScanning) {
                requestAnimationFrame(scanFrame);
            }
        };
        
        scanFrame();
    }
    
    handleDetection(qrCode) {
        const now = Date.now();
        
        // Check cooldown
        if (now - this.lastScanTime < this.scanCooldown) {
            return;
        }
        
        this.lastScanTime = now;
        console.log('QR Code detected:', qrCode);
        
        // Visual feedback
        this.showSuccess(qrCode);
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(200);
        }
        
        // Audio feedback
        this.playBeep();
        
        // Call success callback
        if (this.onSuccess) {
            this.onSuccess(qrCode);
        }
    }
    
    showSuccess(qrCode) {
        this.updateStatus(`Detected: ${qrCode}`);
        
        // Flash effect
        const statusBar = this.container.querySelector('.status-bar');
        statusBar.classList.add('scan-success');
        setTimeout(() => {
            statusBar.classList.remove('scan-success');
            if (this.isScanning) {
                this.updateStatus('Scanning - Point at QR code');
            }
        }, 2000);
    }
    
    playBeep() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.15);
        } catch (e) {
            // Silent fail
        }
    }
    
    updateStatus(message) {
        const statusEl = document.getElementById(`status-${this.containerId}`);
        if (statusEl) {
            statusEl.textContent = message;
        }
    }
    
    stop() {
        this.isScanning = false;
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.scanInterval) {
            clearInterval(this.scanInterval);
            this.scanInterval = null;
        }
        
        this.updateStatus('Scanner stopped');
        console.log('Scanner stopped');
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
}

// Global export
window.NativeQRScanner = NativeQRScanner;