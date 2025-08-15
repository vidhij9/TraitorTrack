/**
 * Live QR Scanner - Fixed camera access implementation
 * Robust camera initialization with proper error handling
 */

class LiveQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.scanner = null;
        this.isScanning = false;
        this.isPaused = false;  // New flag to pause scanning temporarily
        this.onSuccess = null;
        this.cameraStream = null;
        this.permissionManager = new CameraPermissionManager();
        
        console.log('LiveQR: Starting camera-fixed scanner');
        this.init();
    }
    
    async init() {
        this.setupUI();
        this.setupElements();
        this.setupControls();
        
        // Wait a moment for UI to render
        await new Promise(resolve => setTimeout(resolve, 200));
        
        // Auto-start camera with proper permission handling
        await this.startScanning();
    }
    
    setupUI() {
        this.container.innerHTML = `
            <div class="live-qr-scanner">
                <div class="camera-container">
                    <video id="${this.containerId}-video" autoplay playsinline muted></video>
                    <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
                    
                    <!-- Scanning frame -->
                    <div class="scan-overlay">
                        <div class="scan-box">
                            <div class="corner tl"></div>
                            <div class="corner tr"></div>
                            <div class="corner bl"></div>
                            <div class="corner br"></div>
                            <div class="scan-line"></div>
                        </div>
                        <div class="scan-text">Position QR code in frame</div>
                    </div>
                    
                    <!-- Simple controls -->
                    <div class="controls">
                        <button id="torch-btn" class="control-btn" title="Toggle Flash">💡</button>
                    </div>
                    
                    <!-- Success feedback -->
                    <div class="success-flash" id="success-flash"></div>
                </div>
                

            </div>
            
            <style>
                .live-qr-scanner {
                    position: relative;
                    width: 100%;
                    height: 400px;
                    border-radius: 8px;
                    overflow: hidden;
                    background: #000;
                }
                
                .camera-container {
                    position: relative;
                    width: 100%;
                    height: 100%;
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
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: linear-gradient(to right, transparent, #00ff00, transparent);
                    animation: scanning 2s ease-in-out infinite;
                }
                
                @keyframes scanning {
                    0% { top: 0; }
                    50% { top: 196px; }
                    100% { top: 0; }
                }
                
                /* APPLE SPEED: Faster animation for speed perception */
                .scan-line {
                    animation: scanning 1s ease-in-out infinite; /* Faster animation */
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
                    display: flex;
                    gap: 15px;
                    pointer-events: auto;
                }
                
                .control-btn {
                    width: 45px;
                    height: 45px;
                    border-radius: 50%;
                    background: rgba(255,255,255,0.9);
                    border: none;
                    font-size: 18px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .control-btn:hover {
                    background: white;
                    transform: scale(1.1);
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
        // Torch control
        document.getElementById('torch-btn').addEventListener('click', () => {
            this.toggleTorch();
        });
        

    }
    
    async startScanning() {
        console.log('LiveQR: Starting camera with enhanced fallback...');
        
        try {
            // Show initial loading state
            this.showStatus('Requesting camera access...', 'info');
            
            // Check and request camera permission first
            const hasPermission = await this.permissionManager.requestCameraAccess();
            
            if (!hasPermission) {
                throw new Error('Camera permission denied');
            }
            
            // Show loading state
            this.showStatus('Initializing camera...', 'info');
            
            // Try multiple initialization methods with timeout
            await this.tryMultipleInitMethods();
            
        } catch (error) {
            console.error('LiveQR: Camera start failed:', error);
            this.showStatus(`Camera error: ${error.message}. Try manual entry below.`, 'error');
            this.showManualEntryPrompt();
        }
    }
    
    async tryMultipleInitMethods() {
        const methods = [
            () => this.initializeNativeCamera(),
            () => this.tryHtml5Scanner(),
            () => this.initializeBasicCamera()
        ];
        
        for (let i = 0; i < methods.length; i++) {
            try {
                console.log(`LiveQR: Trying initialization method ${i + 1}...`);
                await Promise.race([
                    methods[i](),
                    new Promise((_, reject) => 
                        setTimeout(() => reject(new Error('Method timeout')), 8000)
                    )
                ]);
                console.log(`LiveQR: Method ${i + 1} succeeded`);
                return; // Success, exit
            } catch (error) {
                console.log(`LiveQR: Method ${i + 1} failed:`, error.message);
                if (i === methods.length - 1) {
                    throw new Error('All camera initialization methods failed');
                }
            }
        }
    }
    
    async initializeBasicCamera() {
        console.log('LiveQR: Trying basic camera initialization...');
        
        // Very basic camera constraints for compatibility
        const constraints = {
            video: {
                facingMode: 'environment',
                width: { ideal: 640 },
                height: { ideal: 480 }
            },
            audio: false
        };
        
        this.cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        this.video.srcObject = this.cameraStream;
        await this.video.play();
        
        this.showStatus('Camera active! Point at QR code', 'success');
        this.startDetection();
    }
    
    async tryHtml5Scanner() {
        if (typeof Html5Qrcode === 'undefined') {
            throw new Error('Html5Qrcode not available');
        }
        
        console.log('LiveQR: Starting Html5Qrcode scanner');
        this.scanner = new Html5Qrcode(`${this.containerId}-video`);
        
        const cameras = await Html5Qrcode.getCameras();
        if (cameras.length === 0) {
            throw new Error('No cameras found');
        }
        
        // Use first available camera (prefer back if available)
        let camera = cameras[0];
        for (const cam of cameras) {
            if (cam.label && cam.label.toLowerCase().includes('back')) {
                camera = cam;
                break;
            }
        }
        
        const config = {
            fps: 60,  // APPLE SPEED: Maximum FPS
            qrbox: { width: 250, height: 250 }, // APPLE SPEED: Larger detection box
            aspectRatio: 1.0,
            formatsToSupport: [ Html5QrcodeSupportedFormats.QR_CODE ], // SPEED: QR only
            experimentalFeatures: {
                useBarCodeDetectorIfSupported: true // APPLE SPEED: Use native detection
            }
        };
        
        await this.scanner.start(
            camera.id,
            config,
            (decodedText) => {
                // Respect pause flag to prevent duplicate scans
                if (!this.isPaused) {
                    console.log('LiveQR: QR detected via Html5Qrcode:', decodedText);
                    this.handleSuccess(decodedText);
                }
            },
            () => {
                // Silent error handling
            }
        );
        
        this.isScanning = true;
        console.log('LiveQR: Html5Qrcode scanner started');
    }
    
    async initializeNativeCamera() {
        console.log('LiveQR: Starting native camera');
        
        // Enhanced camera constraints for better compatibility
        const constraints = {
            video: {
                facingMode: { ideal: 'environment' },
                width: { ideal: 1920, min: 1280 }, // APPLE SPEED: Higher resolution for better detection
                height: { ideal: 1080, min: 720 },
                frameRate: { ideal: 60, min: 30 }, // APPLE SPEED: 60fps for ultra-fast scanning
                focusMode: 'continuous',           // APPLE SPEED: Continuous autofocus
                exposureMode: 'continuous',        // APPLE SPEED: Continuous exposure
                whiteBalanceMode: 'continuous'     // APPLE SPEED: Continuous white balance
            },
            audio: false
        };
        
        try {
            this.cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
            console.log('LiveQR: Camera stream obtained');
            this.video.srcObject = this.cameraStream;
            
            // Wait for video to be ready
            await new Promise((resolve, reject) => {
                this.video.onloadedmetadata = () => {
                    this.video.play()
                        .then(resolve)
                        .catch(reject);
                };
                this.video.onerror = reject;
                
                // Timeout after 10 seconds
                setTimeout(() => reject(new Error('Video load timeout')), 10000);
            });
            
            this.isScanning = true;
            this.startNativeScanning();
            this.showStatus('Camera active! Position QR code in frame', 'success');
            console.log('LiveQR: Native camera started successfully');
            
        } catch (error) {
            console.error('LiveQR: Native camera failed:', error);
            
            // Try fallback with simpler constraints
            await this.tryFallbackCamera();
        }
    }
    
    async tryFallbackCamera() {
        console.log('LiveQR: Trying fallback camera settings');
        
        const fallbackConstraints = {
            video: true,
            audio: false
        };
        
        try {
            this.cameraStream = await navigator.mediaDevices.getUserMedia(fallbackConstraints);
            this.video.srcObject = this.cameraStream;
            
            await new Promise((resolve, reject) => {
                this.video.onloadedmetadata = () => {
                    this.video.play()
                        .then(resolve)
                        .catch(reject);
                };
                setTimeout(() => reject(new Error('Fallback timeout')), 5000);
            });
            
            this.isScanning = true;
            this.startNativeScanning();
            this.showStatus('Camera active (fallback mode)', 'success');
            console.log('LiveQR: Fallback camera started');
            
        } catch (error) {
            console.error('LiveQR: All camera attempts failed:', error);
            throw new Error('Unable to access camera. Please check permissions.');
        }
    }
    
    startNativeScanning() {
        if (typeof jsQR === 'undefined') {
            console.log('LiveQR: jsQR not available for native scanning');
            return;
        }
        
        let frame = 0;
        let lastScan = '';
        let lastScanTime = 0;
        
        const scan = () => {
            if (!this.isScanning || this.isPaused) return;
            
            frame++;
            // APPLE SPEED: Scan every frame for ultra-fast detection
            try {
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
                
                if (this.canvas.width > 0 && this.canvas.height > 0) {
                    this.context.drawImage(this.video, 0, 0);
                    
                    // OPTIMIZATION: Scan only center region for faster processing
                    const centerX = Math.floor(this.canvas.width * 0.25);
                    const centerY = Math.floor(this.canvas.height * 0.25);
                    const centerWidth = Math.floor(this.canvas.width * 0.5);
                    const centerHeight = Math.floor(this.canvas.height * 0.5);
                    
                    const imageData = this.context.getImageData(centerX, centerY, centerWidth, centerHeight);
                    const code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: "dontInvert" // SPEED: Skip inversion attempts
                    });
                    
                    if (code && code.data) {
                        const now = Date.now();
                        // APPLE SPEED: Prevent duplicate scans within 200ms
                        if (code.data !== lastScan || (now - lastScanTime) > 200) {
                            console.log('LiveQR: ULTRA-FAST QR detected:', code.data);
                            lastScan = code.data;
                            lastScanTime = now;
                            this.handleSuccess(code.data);
                        }
                    }
                }
            } catch (error) {
                // Silent error handling for continuous scanning
            }
            
            requestAnimationFrame(scan);
        };
        
        scan();
    }
    
    async toggleTorch() {
        try {
            const btn = document.getElementById('torch-btn');
            const track = this.video.srcObject?.getVideoTracks()[0];
            
            if (track && track.getCapabilities && track.getCapabilities().torch) {
                const isOn = btn.classList.contains('active');
                await track.applyConstraints({
                    advanced: [{ torch: !isOn }]
                });
                btn.classList.toggle('active');
            }
        } catch (error) {
            console.log('LiveQR: Torch not supported');
        }
    }
    
    // Manual modal removed
    
    handleSuccess(qrText) {
        // Prevent multiple scans while processing
        if (this.isPaused) {
            return;
        }
        
        console.log('LiveQR: Success:', qrText);
        
        // Pause scanning immediately to prevent duplicate scans
        this.pauseScanning();
        
        // Flash effect
        const flash = document.getElementById('success-flash');
        flash.classList.add('show');
        setTimeout(() => flash.classList.remove('show'), 200);
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(100);
        }
        
        if (this.onSuccess) {
            this.onSuccess(qrText);
        }
        
        // Resume scanning will be called after result is displayed
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
    
    showStatus(message, type = 'info') {
        // Find status container in parent page
        const statusContainer = document.getElementById('result-container');
        if (statusContainer) {
            statusContainer.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'}`;
            statusContainer.innerHTML = `<i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>${message}`;
            statusContainer.style.display = 'block';
        }
    }
    
    async start() {
        if (!this.isScanning) {
            await this.startScanning();
        }
    }
    
    pauseScanning() {
        console.log('LiveQR: Pausing scanner');
        this.isPaused = true;
        
        // Update scan text to show paused state
        const scanText = this.container.querySelector('.scan-text');
        if (scanText) {
            scanText.textContent = 'Processing result...';
        }
    }
    
    resumeScanning() {
        console.log('LiveQR: Resuming scanner');
        this.isPaused = false;
        
        // Update scan text back to normal
        const scanText = this.container.querySelector('.scan-text');
        if (scanText) {
            scanText.textContent = 'Position QR code in frame';
        }
    }
    
    async stop() {
        this.isScanning = false;
        this.isPaused = false;
        
        if (this.scanner && typeof this.scanner.stop === 'function') {
            try {
                await this.scanner.stop();
            } catch (error) {
                console.log('LiveQR: Scanner stop error:', error);
            }
        }
        
        if (this.cameraStream) {
            const tracks = this.cameraStream.getTracks();
            tracks.forEach(track => {
                track.stop();
                console.log('LiveQR: Stopped camera track:', track.kind);
            });
            this.cameraStream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
        
        this.showStatus('Camera stopped', 'info');
        console.log('LiveQR: Camera stopped');
    }
    
    showManualEntryPrompt() {
        // Update result container to encourage manual entry
        const resultContainer = document.getElementById('result-container');
        if (resultContainer) {
            resultContainer.className = 'alert alert-info';
            resultContainer.innerHTML = '<i class="fas fa-keyboard me-2"></i>Camera unavailable. Please use manual entry below.';
        }
    }
}

// Export
window.LiveQRScanner = LiveQRScanner;
console.log('LiveQRScanner loaded - Minimal live scanning ready');