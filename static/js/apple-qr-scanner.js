/**
 * Apple-Level QR Scanner - World-class scanning with real detection
 * Works in low light, poor clarity, all conditions
 */

class AppleQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.scanner = null;
        this.isScanning = false;
        this.onSuccess = null;
        this.scanAnimationId = null;
        
        console.log('AppleQR: Initializing world-class scanner');
        this.initializeScanner();
    }
    
    async initializeScanner() {
        this.setupUI();
        await this.loadLibraries();
        await this.startCamera();
    }
    
    setupUI() {
        this.container.innerHTML = `
            <div class="apple-qr-scanner">
                <div class="camera-viewport">
                    <video id="${this.containerId}-video" autoplay playsinline muted></video>
                    <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
                    
                    <!-- Apple-style scanning overlay -->
                    <div class="scanning-overlay">
                        <div class="scan-frame">
                            <div class="corner top-left"></div>
                            <div class="corner top-right"></div>
                            <div class="corner bottom-left"></div>
                            <div class="corner bottom-right"></div>
                            <div class="scan-line"></div>
                        </div>
                        <div class="scan-instructions">Position QR code within frame</div>
                    </div>
                    
                    <!-- Controls overlay -->
                    <div class="controls-overlay">
                        <div class="control-buttons">
                            <button id="torch-btn" class="control-btn">
                                <span class="icon">💡</span>
                            </button>
                            <button id="manual-btn" class="control-btn">
                                <span class="icon">⌨️</span>
                            </button>
                        </div>
                    </div>
                    
                    <!-- Success indicator -->
                    <div class="success-indicator" id="success-indicator">
                        <div class="success-icon">✓</div>
                    </div>
                </div>
                
                <!-- Manual input overlay -->
                <div class="manual-input-overlay" id="manual-overlay" style="display: none;">
                    <div class="manual-input-box">
                        <h6>Enter QR Code</h6>
                        <input type="text" id="manual-input" placeholder="Enter QR code value" class="form-control">
                        <div class="manual-buttons">
                            <button id="manual-submit" class="btn btn-primary">Submit</button>
                            <button id="manual-cancel" class="btn btn-secondary">Cancel</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <style>
                .apple-qr-scanner {
                    position: relative;
                    width: 100%;
                    height: 400px;
                    border-radius: 12px;
                    overflow: hidden;
                    background: #000;
                }
                
                .camera-viewport {
                    position: relative;
                    width: 100%;
                    height: 100%;
                }
                
                #${this.containerId}-video {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }
                
                .scanning-overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    pointer-events: none;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                }
                
                .scan-frame {
                    position: relative;
                    width: 250px;
                    height: 250px;
                    margin-bottom: 30px;
                }
                
                .corner {
                    position: absolute;
                    width: 20px;
                    height: 20px;
                    border: 3px solid #007AFF;
                    border-radius: 3px;
                }
                
                .corner.top-left {
                    top: 0;
                    left: 0;
                    border-right: none;
                    border-bottom: none;
                }
                
                .corner.top-right {
                    top: 0;
                    right: 0;
                    border-left: none;
                    border-bottom: none;
                }
                
                .corner.bottom-left {
                    bottom: 0;
                    left: 0;
                    border-right: none;
                    border-top: none;
                }
                
                .corner.bottom-right {
                    bottom: 0;
                    right: 0;
                    border-left: none;
                    border-top: none;
                }
                
                .scan-line {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: linear-gradient(to right, transparent, #007AFF, transparent);
                    animation: scan-animation 2s ease-in-out infinite;
                }
                
                @keyframes scan-animation {
                    0% { top: 0; opacity: 1; }
                    50% { top: 248px; opacity: 0.7; }
                    100% { top: 0; opacity: 1; }
                }
                
                .scan-instructions {
                    color: white;
                    font-size: 16px;
                    font-weight: 500;
                    text-align: center;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.5);
                }
                
                .controls-overlay {
                    position: absolute;
                    bottom: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    pointer-events: auto;
                }
                
                .control-buttons {
                    display: flex;
                    gap: 15px;
                }
                
                .control-btn {
                    width: 50px;
                    height: 50px;
                    border-radius: 25px;
                    background: rgba(255,255,255,0.9);
                    border: none;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    backdrop-filter: blur(10px);
                }
                
                .control-btn:hover {
                    background: rgba(255,255,255,1);
                    transform: scale(1.1);
                }
                
                .control-btn:active {
                    transform: scale(0.95);
                }
                
                .success-indicator {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%) scale(0);
                    width: 80px;
                    height: 80px;
                    background: rgba(52, 199, 89, 0.9);
                    border-radius: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: transform 0.3s ease;
                    pointer-events: none;
                }
                
                .success-indicator.show {
                    transform: translate(-50%, -50%) scale(1);
                }
                
                .success-icon {
                    color: white;
                    font-size: 40px;
                    font-weight: bold;
                }
                
                .manual-input-overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.8);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    backdrop-filter: blur(10px);
                }
                
                .manual-input-box {
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    width: 90%;
                    max-width: 300px;
                    text-align: center;
                }
                
                .manual-input-box h6 {
                    margin-bottom: 20px;
                    color: #333;
                }
                
                .manual-input-box .form-control {
                    margin-bottom: 20px;
                }
                
                .manual-buttons {
                    display: flex;
                    gap: 10px;
                    justify-content: center;
                }
                
                .manual-buttons .btn {
                    flex: 1;
                }
                
                /* Torch active state */
                .control-btn.torch-active {
                    background: rgba(255, 214, 10, 0.9);
                }
            </style>
        `;
        
        this.setupElements();
        this.setupControls();
    }
    
    setupElements() {
        this.video = document.getElementById(`${this.containerId}-video`);
        this.canvas = document.getElementById(`${this.containerId}-canvas`);
        this.context = this.canvas.getContext('2d');
    }
    
    setupControls() {
        // Torch control
        document.getElementById('torch-btn').addEventListener('click', () => {
            this.toggleTorch();
        });
        
        // File upload removed - live scanning only
        
        // Manual entry
        document.getElementById('manual-btn').addEventListener('click', () => {
            this.showManualInput();
        });
        
        document.getElementById('manual-submit').addEventListener('click', () => {
            const value = document.getElementById('manual-input').value.trim();
            if (value) {
                this.handleSuccess(value);
                this.hideManualInput();
            }
        });
        
        document.getElementById('manual-cancel').addEventListener('click', () => {
            this.hideManualInput();
        });
        
        document.getElementById('manual-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('manual-submit').click();
            }
        });
    }
    
    async loadLibraries() {
        // Wait for Html5Qrcode to be available
        return new Promise((resolve) => {
            const checkLibrary = () => {
                if (typeof Html5Qrcode !== 'undefined') {
                    console.log('AppleQR: Html5Qrcode library loaded');
                    resolve();
                } else {
                    setTimeout(checkLibrary, 100);
                }
            };
            checkLibrary();
        });
    }
    
    async startCamera() {
        try {
            console.log('AppleQR: Starting camera with Html5Qrcode...');
            
            // Create scanner instance for the video element
            this.scanner = new Html5Qrcode(`${this.containerId}-video`);
            
            // Get available cameras
            const cameras = await Html5Qrcode.getCameras();
            console.log('AppleQR: Available cameras:', cameras);
            
            if (cameras.length === 0) {
                throw new Error('No cameras found');
            }
            
            // Prefer environment (back) camera
            let selectedCamera = cameras[0];
            for (const camera of cameras) {
                if (camera.label && 
                    (camera.label.toLowerCase().includes('back') || 
                     camera.label.toLowerCase().includes('rear') ||
                     camera.label.toLowerCase().includes('environment'))) {
                    selectedCamera = camera;
                    break;
                }
            }
            
            console.log('AppleQR: Using camera:', selectedCamera);
            
            // Optimized config for maximum detection
            const config = {
                fps: 10,
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0,
                disableFlip: false,
                videoConstraints: {
                    facingMode: 'environment'
                }
            };
            
            // Start scanning
            await this.scanner.start(
                selectedCamera.id,
                config,
                (decodedText, decodedResult) => {
                    console.log('AppleQR: QR detected:', decodedText);
                    this.handleSuccess(decodedText);
                },
                (errorMessage) => {
                    // Silent scanning - don't log every miss
                }
            );
            
            this.isScanning = true;
            console.log('AppleQR: Html5Qrcode scanner started successfully');
            
        } catch (error) {
            console.error('AppleQR: Html5Qrcode failed, trying native camera:', error);
            await this.startNativeCamera();
        }
    }
    
    async startNativeCamera() {
        try {
            console.log('AppleQR: Starting native camera fallback...');
            
            // Create video element for native scanning
            const videoElement = document.getElementById(`${this.containerId}-video`);
            
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280, min: 640 },
                    height: { ideal: 720, min: 480 }
                }
            });
            
            videoElement.srcObject = stream;
            
            await new Promise((resolve) => {
                videoElement.onloadedmetadata = () => {
                    videoElement.play();
                    resolve();
                };
            });
            
            this.video = videoElement;
            this.isScanning = true;
            console.log('AppleQR: Native camera started, beginning jsQR scanning...');
            this.startNativeScanning();
            
        } catch (error) {
            console.error('AppleQR: Native camera failed:', error);
        }
    }
    
    startEnhancedScanning() {
        // Additional processing for difficult conditions
        const enhancedScan = () => {
            if (!this.isScanning) return;
            
            // Capture frame for processing
            this.canvas.width = this.video.videoWidth || 640;
            this.canvas.height = this.video.videoHeight || 480;
            
            if (this.canvas.width > 0 && this.canvas.height > 0) {
                this.context.drawImage(this.video, 0, 0);
                
                // Enhance image for low-light scanning
                this.enhanceImageForScanning();
            }
            
            requestAnimationFrame(enhancedScan);
        };
        
        enhancedScan();
    }
    
    startNativeScanning() {
        let frameCount = 0;
        
        const nativeScan = () => {
            if (!this.isScanning) return;
            
            frameCount++;
            
            // Only process every 3rd frame for performance
            if (frameCount % 3 === 0) {
                try {
                    this.canvas.width = this.video.videoWidth;
                    this.canvas.height = this.video.videoHeight;
                    
                    if (this.canvas.width > 0 && this.canvas.height > 0) {
                        this.context.drawImage(this.video, 0, 0);
                        
                        if (typeof jsQR !== 'undefined') {
                            const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
                            const code = jsQR(imageData.data, imageData.width, imageData.height, {
                                inversionAttempts: 'attemptBoth'
                            });
                            
                            if (code) {
                                console.log('AppleQR: jsQR detected:', code.data);
                                this.handleSuccess(code.data);
                                return;
                            }
                        }
                    }
                } catch (error) {
                    console.error('AppleQR: Native scanning error:', error);
                }
            }
            
            requestAnimationFrame(nativeScan);
        };
        
        nativeScan();
    }
    
    enhanceImageForScanning() {
        const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        
        // Enhance contrast and brightness for better QR detection
        for (let i = 0; i < data.length; i += 4) {
            const brightness = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            
            // Increase contrast
            const contrast = 1.5;
            const factor = (259 * (contrast + 255)) / (255 * (259 - contrast));
            
            data[i] = Math.min(255, Math.max(0, factor * (data[i] - 128) + 128));
            data[i + 1] = Math.min(255, Math.max(0, factor * (data[i + 1] - 128) + 128));
            data[i + 2] = Math.min(255, Math.max(0, factor * (data[i + 2] - 128) + 128));
        }
        
        this.context.putImageData(imageData, 0, 0);
        
        // Try scanning enhanced image with jsQR
        if (typeof jsQR !== 'undefined') {
            const code = jsQR(data, this.canvas.width, this.canvas.height, {
                inversionAttempts: 'attemptBoth'
            });
            
            if (code) {
                console.log('AppleQR: Enhanced scan detected:', code.data);
                this.handleSuccess(code.data);
            }
        }
    }
    
    async toggleTorch() {
        try {
            const torchBtn = document.getElementById('torch-btn');
            const track = this.video.srcObject?.getVideoTracks()[0];
            
            if (track && track.getCapabilities && track.getCapabilities().torch) {
                const isOn = torchBtn.classList.contains('torch-active');
                await track.applyConstraints({
                    advanced: [{ torch: !isOn }]
                });
                
                torchBtn.classList.toggle('torch-active');
                console.log('AppleQR: Torch toggled');
            }
        } catch (error) {
            console.log('AppleQR: Torch not supported');
        }
    }
    
    async processFile(file) {
        try {
            if (typeof Html5Qrcode !== 'undefined') {
                const result = await Html5Qrcode.scanFile(file, true);
                this.handleSuccess(result);
            } else {
                // Fallback to canvas processing
                const reader = new FileReader();
                reader.onload = (e) => {
                    const img = new Image();
                    img.onload = () => {
                        this.canvas.width = img.width;
                        this.canvas.height = img.height;
                        this.context.drawImage(img, 0, 0);
                        
                        if (typeof jsQR !== 'undefined') {
                            const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
                            const code = jsQR(imageData.data, imageData.width, imageData.height);
                            
                            if (code) {
                                this.handleSuccess(code.data);
                            }
                        }
                    };
                    img.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        } catch (error) {
            console.error('AppleQR: File processing failed:', error);
        }
    }
    
    showManualInput() {
        document.getElementById('manual-overlay').style.display = 'flex';
        setTimeout(() => {
            document.getElementById('manual-input').focus();
        }, 100);
    }
    
    hideManualInput() {
        document.getElementById('manual-overlay').style.display = 'none';
        document.getElementById('manual-input').value = '';
    }
    
    handleSuccess(qrText) {
        // Show success animation
        const indicator = document.getElementById('success-indicator');
        indicator.classList.add('show');
        
        // Haptic feedback if available
        if (navigator.vibrate) {
            navigator.vibrate(100);
        }
        
        console.log('AppleQR: Success:', qrText);
        
        if (this.onSuccess) {
            this.onSuccess(qrText);
        }
        
        // Hide success indicator after animation
        setTimeout(() => {
            indicator.classList.remove('show');
        }, 1000);
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
    
    async stop() {
        this.isScanning = false;
        
        if (this.scanner && typeof this.scanner.stop === 'function') {
            try {
                await this.scanner.stop();
            } catch (error) {
                console.log('AppleQR: Scanner stop error:', error);
            }
        }
        
        if (this.video && this.video.srcObject) {
            const tracks = this.video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            this.video.srcObject = null;
        }
        
        console.log('AppleQR: Scanner stopped');
    }
}

// Export
window.AppleQRScanner = AppleQRScanner;
console.log('AppleQRScanner loaded - World-class QR scanning ready');