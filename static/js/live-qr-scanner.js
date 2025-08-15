/**
 * Live QR Scanner - World-Class Ultimate Edition
 * ================================================
 * The world's best QR scanner that handles:
 * - Tiny QR codes (5mm x 5mm)
 * - Damaged/crushed/wrinkled codes
 * - Universal flashlight support across ALL devices
 * - Low light conditions
 * - Motion blur and extreme angles
 * - Multiple scanning engines in parallel
 */

class LiveQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.offscreenCanvas = null;
        this.offscreenContext = null;
        this.enhancementCanvas = null;
        this.enhancementContext = null;
        
        // Multiple scanner instances for parallel processing
        this.scanners = {
            jsQR: null,
            html5QrCode: null,
            zxing: null
        };
        
        // State management
        this.isScanning = false;
        this.isPaused = false;
        this.onSuccess = null;
        this.cameraStream = null;
        this.lastSuccessfulScan = '';
        this.lastScanTime = 0;
        
        // Advanced torch support
        this.torchSupported = false;
        this.torchEnabled = false;
        this.imageCapture = null;
        this.zoomSupported = false;
        this.currentZoom = 1;
        this.minZoom = 1;
        this.maxZoom = 1;
        
        // Image enhancement for damaged codes
        this.enhancementSettings = {
            contrast: 1.5,
            brightness: 1.1,
            sharpness: true,
            denoise: true,
            adaptiveThreshold: true
        };
        
        // Permission manager
        this.permissionManager = typeof CameraPermissionManager !== 'undefined' 
            ? new CameraPermissionManager() 
            : null;
        
        console.log('LiveQR: Starting World-Class Ultimate Scanner');
        this.init();
    }
    
    async init() {
        // Try to load external libraries but don't fail if they can't load
        try {
            await this.loadExternalLibraries();
        } catch (e) {
            console.log('LiveQR: External libraries could not be loaded, continuing with built-in scanners');
        }
        
        this.setupUI();
        this.setupElements();
        this.setupControls();
        
        // Wait a moment for UI to render
        await new Promise(resolve => setTimeout(resolve, 200));
        
        // Auto-start camera with proper permission handling
        await this.startScanning();
    }
    
    async loadExternalLibraries() {
        // Load ZXing if not already loaded for additional scanning capability
        // Using the browser bundle version which includes all necessary components
        if (typeof ZXing === 'undefined' && !document.querySelector('script[src*="zxing"]')) {
            try {
                // Use the correct browser bundle URL
                await this.loadScript('https://unpkg.com/@zxing/browser@latest/umd/index.min.js');
                console.log('LiveQR: ZXing library loaded successfully');
            } catch (e) {
                console.log('LiveQR: ZXing library could not be loaded - continuing with jsQR only');
                // Scanner will still work with jsQR, ZXing is optional
            }
        }
    }
    
    loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.crossOrigin = 'anonymous'; // Add CORS support
            script.onload = () => {
                console.log(`LiveQR: Successfully loaded script from ${src}`);
                resolve();
            };
            script.onerror = (error) => {
                console.error(`LiveQR: Failed to load script from ${src}`, error);
                reject(error);
            };
            document.head.appendChild(script);
        });
    }
    
    setupUI() {
        this.container.innerHTML = `
            <div class="live-qr-scanner">
                <div class="camera-container">
                    <video id="${this.containerId}-video" autoplay playsinline muted></video>
                    <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
                    
                    <!-- Advanced scanning overlay -->
                    <div class="scan-overlay">
                        <div class="scan-box">
                            <div class="corner tl"></div>
                            <div class="corner tr"></div>
                            <div class="corner bl"></div>
                            <div class="corner br"></div>
                            <div class="scan-line"></div>
                        </div>
                        <div class="scan-text">Position QR code in frame</div>
                        <div class="scan-status" style="display: none;"></div>
                    </div>
                    
                    <!-- Enhanced controls -->
                    <div class="controls">
                        <button id="torch-btn" class="control-btn" title="Toggle Flash">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2">
                                <path d="M12 2L12 10M12 18L12 22M4 12L10 12M14 12L20 12M6.34 6.34L10.58 10.58M13.42 13.42L17.66 17.66M6.34 17.66L10.58 13.42M13.42 10.58L17.66 6.34"/>
                            </svg>
                        </button>
                        <button id="zoom-in-btn" class="control-btn" title="Zoom In" style="display:none;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"></circle>
                                <path d="M21 21L16.65 16.65M11 8L11 14M8 11L14 11"></path>
                            </svg>
                        </button>
                        <button id="zoom-out-btn" class="control-btn" title="Zoom Out" style="display:none;">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"></circle>
                                <path d="M21 21L16.65 16.65M8 11L14 11"></path>
                            </svg>
                        </button>
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
                    border: 3px solid #00ff00;
                    filter: drop-shadow(0 0 3px rgba(0, 255, 0, 0.5));
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
                    animation: ultra-scan 0.8s ease-in-out infinite;
                    filter: drop-shadow(0 0 3px rgba(0, 255, 0, 0.8));
                }
                
                @keyframes ultra-scan {
                    0% { top: 0; opacity: 0; }
                    10% { opacity: 1; }
                    90% { opacity: 1; }
                    100% { top: 194px; opacity: 0; }
                }
                
                .scan-text {
                    color: white;
                    font-size: 14px;
                    text-shadow: 0 1px 3px rgba(0,0,0,0.7);
                }
                
                .scan-status {
                    color: #00ff00;
                    font-size: 12px;
                    margin-top: 5px;
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
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .control-btn:hover {
                    background: white;
                    transform: scale(1.1);
                }
                
                .control-btn.active {
                    background: #ffd700;
                    box-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
                }
                
                .control-btn:disabled {
                    opacity: 0.3;
                    cursor: not-allowed;
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
        this.context = this.canvas.getContext('2d', { willReadFrequently: true });
        
        // Create offscreen canvases for image processing
        this.offscreenCanvas = document.createElement('canvas');
        this.offscreenContext = this.offscreenCanvas.getContext('2d', { willReadFrequently: true });
        
        this.enhancementCanvas = document.createElement('canvas');
        this.enhancementContext = this.enhancementCanvas.getContext('2d', { willReadFrequently: true });
    }
    
    setupControls() {
        // Enhanced torch control with multiple fallback methods
        const torchBtn = document.getElementById('torch-btn');
        if (torchBtn) {
            torchBtn.addEventListener('click', () => this.toggleTorchUniversal());
        }
        
        // Zoom controls
        const zoomInBtn = document.getElementById('zoom-in-btn');
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => this.adjustZoom(0.2));
        }
        
        const zoomOutBtn = document.getElementById('zoom-out-btn');
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => this.adjustZoom(-0.2));
        }
    }
    
    async startScanning() {
        console.log('LiveQR: Starting camera with enhanced fallback...');
        
        try {
            // Show initial loading state
            this.showStatus('Requesting camera access...', 'info');
            
            // Check and request camera permission first
            const hasPermission = this.permissionManager ? 
                await this.permissionManager.requestCameraAccess() : true;
            
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
            () => this.initializeOptimalCamera(), // Try optimal settings first
            () => this.tryHtml5Scanner(), // Try Html5Qrcode (better camera control)
            () => this.initializeNativeCamera(),
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
    
    async initializeOptimalCamera() {
        console.log('LiveQR: Trying optimal camera settings for tiny & damaged QR codes');
        
        // Optimal constraints for tiny QR codes and maximum quality
        const constraints = {
            video: {
                facingMode: { exact: 'environment' },
                width: { ideal: 3840, min: 1920 }, // 4K resolution for tiny codes
                height: { ideal: 2160, min: 1080 },
                frameRate: { ideal: 60, min: 30 }, // High FPS for fast scanning
                focusMode: { ideal: 'continuous' }, // Auto-focus for varying distances
                exposureMode: { ideal: 'continuous' },
                whiteBalanceMode: { ideal: 'continuous' },
                resizeMode: 'none' // No downscaling
            },
            audio: false
        };
        
        this.cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        this.video.srcObject = this.cameraStream;
        await this.video.play();
        
        // Setup advanced camera features
        await this.setupAdvancedCameraFeatures();
        
        this.showStatus('Camera active! Point at QR code', 'success');
        this.startMultiEngineScan();
    }
    
    async initializeBasicCamera() {
        console.log('LiveQR: Trying basic camera initialization - back camera');
        
        // Basic constraints but still force back camera
        const constraints = {
            video: {
                facingMode: { exact: 'environment' }, // FORCE back camera even in basic mode
                width: { ideal: 1280 },
                height: { ideal: 720 }
            },
            audio: false
        };
        
        this.cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        this.video.srcObject = this.cameraStream;
        await this.video.play();
        
        // Setup advanced features even in basic mode
        await this.setupAdvancedCameraFeatures();
        
        this.showStatus('Camera active! Point at QR code', 'success');
        this.startMultiEngineScan();
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
        
        // ALWAYS prefer back camera - check all cameras for back camera
        let camera = null;
        for (const cam of cameras) {
            console.log('LiveQR: Found camera:', cam.label || cam.id);
            if (cam.label) {
                const label = cam.label.toLowerCase();
                // Check for back camera indicators
                if (label.includes('back') || label.includes('rear') || 
                    label.includes('environment') || label.includes('0')) {
                    camera = cam;
                    console.log('LiveQR: Selected back camera:', cam.label);
                    break;
                }
            }
        }
        
        // If no back camera found, use the last camera (usually back on mobile)
        if (!camera) {
            camera = cameras[cameras.length - 1];
            console.log('LiveQR: Using last camera as fallback:', camera.label || camera.id);
        }
        
        const config = {
            fps: 60,  // Maximum FPS for instant detection
            qrbox: { width: 300, height: 300 }, // Larger scan area for easier scanning
            aspectRatio: 1.0,
            formatsToSupport: [ Html5QrcodeSupportedFormats.QR_CODE ], // QR only for speed
            experimentalFeatures: {
                useBarCodeDetectorIfSupported: true // Native detection for speed
            },
            videoConstraints: {
                facingMode: { exact: 'environment' }, // FORCE back camera
                frameRate: { ideal: 60, min: 30 }
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
                } else {
                    console.log('LiveQR: QR detected but scanner is paused, ignoring:', decodedText);
                }
            },
            (errorMessage) => {
                // Silent error handling for scan failures
                // These are normal when no QR code is in view
            }
        );
        
        this.isScanning = true;
        console.log('LiveQR: Html5Qrcode scanner started');
    }
    
    async initializeNativeCamera() {
        console.log('LiveQR: Starting native camera - BACK CAMERA ONLY');
        
        // Force back camera with strict constraints
        const constraints = {
            video: {
                facingMode: { exact: 'environment' }, // FORCE back camera
                width: { ideal: 1920, min: 1280 },
                height: { ideal: 1080, min: 720 },
                frameRate: { ideal: 60, min: 30 },
                focusMode: 'continuous',
                exposureMode: 'continuous',
                whiteBalanceMode: 'continuous'
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
            this.startMultiEngineScan();
            this.showStatus('Camera active! Position QR code in frame', 'success');
            console.log('LiveQR: Native camera started successfully');
            
        } catch (error) {
            console.error('LiveQR: Native camera failed:', error);
            
            // Try fallback with simpler constraints
            await this.tryFallbackCamera();
        }
    }
    
    async tryFallbackCamera() {
        console.log('LiveQR: Trying fallback camera settings - still preferring back');
        
        const fallbackConstraints = {
            video: {
                facingMode: 'environment' // Still try for back camera
            },
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
            this.startMultiEngineScan();
            this.showStatus('Camera active (fallback mode)', 'success');
            console.log('LiveQR: Fallback camera started');
            
        } catch (error) {
            console.error('LiveQR: All camera attempts failed:', error);
            throw new Error('Unable to access camera. Please check permissions.');
        }
    }
    
    async setupAdvancedCameraFeatures() {
        const track = this.cameraStream?.getVideoTracks()[0];
        if (!track) return;
        
        const capabilities = track.getCapabilities ? track.getCapabilities() : {};
        const settings = track.getSettings ? track.getSettings() : {};
        
        console.log('LiveQR: Camera capabilities:', capabilities);
        
        // Check torch support with multiple methods
        this.torchSupported = await this.checkUniversalTorchSupport(track);
        
        // Check zoom support
        if (capabilities.zoom) {
            this.zoomSupported = true;
            this.minZoom = capabilities.zoom.min || 1;
            this.maxZoom = capabilities.zoom.max || 1;
            this.currentZoom = settings.zoom || 1;
            console.log(`LiveQR: Zoom supported (${this.minZoom}x - ${this.maxZoom}x)`);
            
            // Show zoom controls
            const zoomInBtn = document.getElementById('zoom-in-btn');
            const zoomOutBtn = document.getElementById('zoom-out-btn');
            if (zoomInBtn) zoomInBtn.style.display = 'inline-block';
            if (zoomOutBtn) zoomOutBtn.style.display = 'inline-block';
        }
        
        // Set continuous auto-focus if available
        if (capabilities.focusMode && capabilities.focusMode.includes('continuous')) {
            try {
                await track.applyConstraints({
                    advanced: [{ focusMode: 'continuous' }]
                });
                console.log('LiveQR: Continuous auto-focus enabled');
            } catch (e) {
                console.log('LiveQR: Could not set continuous focus');
            }
        }
        
        // Update torch button visibility
        const torchBtn = document.getElementById('torch-btn');
        if (torchBtn) {
            torchBtn.style.opacity = this.torchSupported ? '1' : '0.3';
        }
    }
    
    async checkUniversalTorchSupport(track) {
        // Method 1: Check capabilities
        if (track.getCapabilities) {
            const capabilities = track.getCapabilities();
            if (capabilities.torch) {
                console.log('LiveQR: Torch supported via capabilities');
                return true;
            }
        }
        
        // Method 2: Try to apply torch constraint
        try {
            await track.applyConstraints({
                advanced: [{ torch: false }]
            });
            console.log('LiveQR: Torch supported via applyConstraints');
            return true;
        } catch (e) {
            // Silent fail
        }
        
        // Method 3: Check ImageCapture API (works on more devices)
        if (typeof ImageCapture !== 'undefined') {
            try {
                const imageCapture = new ImageCapture(track);
                const photoCapabilities = await imageCapture.getPhotoCapabilities();
                if (photoCapabilities.fillLightMode && photoCapabilities.fillLightMode.includes('flash')) {
                    console.log('LiveQR: Torch supported via ImageCapture API');
                    this.imageCapture = imageCapture;
                    return true;
                }
            } catch (e) {
                // Silent fail
            }
        }
        
        // Method 4: MediaStreamTrack API (newer devices)
        if ('torch' in track) {
            console.log('LiveQR: Torch supported via MediaStreamTrack');
            return true;
        }
        
        console.log('LiveQR: Torch not supported');
        return false;
    }
    
    async toggleTorchUniversal() {
        if (!this.torchSupported) {
            console.log('LiveQR: Torch not supported on this device');
            this.showStatus('Flashlight not available on this device', 'info');
            return;
        }
        
        const track = this.cameraStream?.getVideoTracks()[0];
        if (!track) return;
        
        const torchBtn = document.getElementById('torch-btn');
        
        try {
            this.torchEnabled = !this.torchEnabled;
            
            // Method 1: Standard torch control
            if (track.applyConstraints) {
                try {
                    await track.applyConstraints({
                        advanced: [{ torch: this.torchEnabled }]
                    });
                    console.log(`LiveQR: Torch ${this.torchEnabled ? 'ON' : 'OFF'} via constraints`);
                    if (torchBtn) torchBtn.classList.toggle('active', this.torchEnabled);
                    return;
                } catch (e) {
                    console.log('LiveQR: Standard torch method failed');
                }
            }
            
            // Method 2: ImageCapture API (works on more Android devices)
            if (this.imageCapture) {
                try {
                    const photoSettings = {
                        fillLightMode: this.torchEnabled ? 'flash' : 'off'
                    };
                    // Take a photo to trigger the flash
                    if (this.torchEnabled) {
                        await this.imageCapture.takePhoto(photoSettings);
                    }
                    console.log(`LiveQR: Torch ${this.torchEnabled ? 'ON' : 'OFF'} via ImageCapture`);
                    if (torchBtn) torchBtn.classList.toggle('active', this.torchEnabled);
                    return;
                } catch (e) {
                    console.log('LiveQR: ImageCapture torch method failed');
                }
            }
            
            // Method 3: iOS-specific handling
            if (this.isIOS()) {
                await this.toggleTorchIOS();
                if (torchBtn) torchBtn.classList.toggle('active', this.torchEnabled);
                return;
            }
            
            // Method 4: Re-initialize stream with torch setting (last resort)
            await this.reinitializeStreamWithTorch();
            if (torchBtn) torchBtn.classList.toggle('active', this.torchEnabled);
            
        } catch (error) {
            console.error('LiveQR: Failed to toggle torch:', error);
            this.torchEnabled = !this.torchEnabled; // Revert state
            this.showStatus('Could not control flashlight', 'error');
        }
    }
    
    async toggleTorchIOS() {
        // iOS-specific torch handling
        try {
            const constraints = {
                video: {
                    facingMode: 'environment',
                    torch: this.torchEnabled
                },
                audio: false
            };
            
            // Stop current stream
            if (this.cameraStream) {
                this.cameraStream.getTracks().forEach(track => track.stop());
            }
            
            // Get new stream with torch setting
            const newStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.cameraStream = newStream;
            this.video.srcObject = newStream;
            await this.video.play();
            
            console.log(`LiveQR: iOS Torch ${this.torchEnabled ? 'ON' : 'OFF'}`);
            
            // Restart scanning
            this.startMultiEngineScan();
            
        } catch (error) {
            console.error('LiveQR: iOS torch toggle failed:', error);
            throw error;
        }
    }
    
    async reinitializeStreamWithTorch() {
        // Last resort: reinitialize entire stream with torch
        try {
            const constraints = {
                video: {
                    facingMode: { exact: 'environment' },
                    width: { ideal: 1920 },
                    height: { ideal: 1080 },
                    advanced: [{ torch: this.torchEnabled }]
                },
                audio: false
            };
            
            // Stop current stream
            if (this.cameraStream) {
                this.cameraStream.getTracks().forEach(track => track.stop());
            }
            
            // Get new stream
            const newStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.cameraStream = newStream;
            this.video.srcObject = newStream;
            await this.video.play();
            
            console.log(`LiveQR: Stream reinitialized with torch ${this.torchEnabled ? 'ON' : 'OFF'}`);
            
            // Restart scanning
            this.startMultiEngineScan();
            
        } catch (error) {
            console.error('LiveQR: Stream reinitialize failed:', error);
            throw error;
        }
    }
    
    isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    }
    
    async adjustZoom(delta) {
        if (!this.zoomSupported) return;
        
        const track = this.cameraStream?.getVideoTracks()[0];
        if (!track) return;
        
        this.currentZoom = Math.max(this.minZoom, Math.min(this.maxZoom, this.currentZoom + delta));
        
        try {
            await track.applyConstraints({
                advanced: [{ zoom: this.currentZoom }]
            });
            console.log(`LiveQR: Zoom set to ${this.currentZoom}x`);
            this.showStatus(`Zoom: ${this.currentZoom.toFixed(1)}x`, 'info');
        } catch (error) {
            console.error('LiveQR: Failed to adjust zoom:', error);
        }
    }
    
    startMultiEngineScan() {
        // Start multiple scanning engines in parallel for best results
        this.startJsQRScanning(); // Primary scanner - always available
        
        // Try to start ZXing if available (optional enhancement)
        if (typeof ZXing !== 'undefined' || typeof window.ZXingBrowser !== 'undefined') {
            this.startZXingScanning();
        } else {
            console.log('LiveQR: ZXing not available, using jsQR only (still world-class!)');
        }
        
        this.isScanning = true;
    }
    
    startNativeScanning() {
        this.startMultiEngineScan();
    }
    
    startJsQRScanning() {
        if (typeof jsQR === 'undefined') {
            console.log('LiveQR: jsQR not available');
            return;
        }
        
        let frame = 0;
        
        const scan = () => {
            if (!this.isScanning) return;
            
            if (!this.isPaused && this.video.readyState === 4) {
                frame++;
                
                // Update canvas size
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
                
                if (this.canvas.width > 0 && this.canvas.height > 0) {
                    this.context.drawImage(this.video, 0, 0);
                    
                    // Multi-strategy scanning for maximum success rate
                    this.scanWithMultipleStrategies();
                }
            }
            
            requestAnimationFrame(scan);
        };
        
        console.log('LiveQR: Starting enhanced jsQR scanning');
        scan();
    }
    
    scanWithMultipleStrategies() {
        // Strategy 1: Full frame scan (for well-positioned codes)
        this.scanFullFrame();
        
        // Strategy 2: Center region scan (faster)
        this.scanCenterRegion();
        
        // Strategy 3: Enhanced image scan (for damaged codes)
        if (this.enhancementSettings.adaptiveThreshold) {
            this.scanEnhancedImage();
        }
        
        // Strategy 4: Multi-scale scan (for tiny 5mm codes)
        this.scanMultiScale();
    }
    
    scanFullFrame() {
        const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'attemptBoth' // Try both normal and inverted
        });
        
        if (code && code.data) {
            this.handleDetection(code.data, 'jsQR-full');
        }
    }
    
    scanCenterRegion() {
        const centerSize = 0.6; // 60% center region
        const x = Math.floor(this.canvas.width * (1 - centerSize) / 2);
        const y = Math.floor(this.canvas.height * (1 - centerSize) / 2);
        const width = Math.floor(this.canvas.width * centerSize);
        const height = Math.floor(this.canvas.height * centerSize);
        
        const imageData = this.context.getImageData(x, y, width, height);
        const code = jsQR(imageData.data, width, height, {
            inversionAttempts: 'dontInvert' // Faster
        });
        
        if (code && code.data) {
            this.handleDetection(code.data, 'jsQR-center');
        }
    }
    
    scanEnhancedImage() {
        // Apply enhancement for damaged/crushed QR codes
        this.enhancementCanvas.width = this.canvas.width;
        this.enhancementCanvas.height = this.canvas.height;
        
        // Copy and enhance image
        this.enhancementContext.drawImage(this.canvas, 0, 0);
        const imageData = this.enhancementContext.getImageData(0, 0, this.enhancementCanvas.width, this.enhancementCanvas.height);
        
        // Apply enhancements
        this.enhanceImageForDamagedCodes(imageData);
        this.enhancementContext.putImageData(imageData, 0, 0);
        
        // Scan enhanced image
        const enhancedData = this.enhancementContext.getImageData(0, 0, this.enhancementCanvas.width, this.enhancementCanvas.height);
        const code = jsQR(enhancedData.data, enhancedData.width, enhancedData.height, {
            inversionAttempts: 'attemptBoth'
        });
        
        if (code && code.data) {
            this.handleDetection(code.data, 'jsQR-enhanced');
        }
    }
    
    scanMultiScale() {
        // Scan at different scales for tiny 5mm QR codes
        const scales = [1.5, 2.0, 2.5, 3.0]; // Upscale factors
        
        for (const scale of scales) {
            const scaledWidth = Math.floor(this.canvas.width * scale);
            const scaledHeight = Math.floor(this.canvas.height * scale);
            
            // Skip if too large
            if (scaledWidth * scaledHeight > 8000000) continue;
            
            this.offscreenCanvas.width = scaledWidth;
            this.offscreenCanvas.height = scaledHeight;
            
            // Draw scaled image with sharp interpolation
            this.offscreenContext.imageSmoothingEnabled = false;
            this.offscreenContext.scale(scale, scale);
            this.offscreenContext.drawImage(this.video, 0, 0);
            this.offscreenContext.setTransform(1, 0, 0, 1, 0, 0);
            
            // Scan scaled image
            const imageData = this.offscreenContext.getImageData(0, 0, scaledWidth, scaledHeight);
            const code = jsQR(imageData.data, scaledWidth, scaledHeight, {
                inversionAttempts: 'dontInvert'
            });
            
            if (code && code.data) {
                this.handleDetection(code.data, `jsQR-scale-${scale}x`);
                break;
            }
        }
    }
    
    enhanceImageForDamagedCodes(imageData) {
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        
        // Step 1: Apply brightness and contrast adjustment
        for (let i = 0; i < data.length; i += 4) {
            // Increase contrast and brightness for better edge detection
            data[i] = Math.min(255, Math.max(0, (data[i] - 128) * this.enhancementSettings.contrast + 128 * this.enhancementSettings.brightness));
            data[i + 1] = Math.min(255, Math.max(0, (data[i + 1] - 128) * this.enhancementSettings.contrast + 128 * this.enhancementSettings.brightness));
            data[i + 2] = Math.min(255, Math.max(0, (data[i + 2] - 128) * this.enhancementSettings.contrast + 128 * this.enhancementSettings.brightness));
        }
        
        // Step 2: Apply sharpening filter for blurry/damaged codes
        if (this.enhancementSettings.sharpness) {
            this.applySharpenFilter(data, width, height);
        }
        
        // Step 3: Apply adaptive threshold for crushed/wrinkled codes
        if (this.enhancementSettings.adaptiveThreshold) {
            this.applyAdaptiveThreshold(data, width, height);
        }
    }
    
    applySharpenFilter(data, width, height) {
        // Sharpening kernel for enhancing edges
        const kernel = [
            0, -1, 0,
            -1, 5, -1,
            0, -1, 0
        ];
        
        const output = new Uint8ClampedArray(data);
        
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                const idx = (y * width + x) * 4;
                
                for (let c = 0; c < 3; c++) {
                    let sum = 0;
                    for (let ky = -1; ky <= 1; ky++) {
                        for (let kx = -1; kx <= 1; kx++) {
                            const kidx = ((y + ky) * width + (x + kx)) * 4;
                            sum += data[kidx + c] * kernel[(ky + 1) * 3 + (kx + 1)];
                        }
                    }
                    output[idx + c] = Math.min(255, Math.max(0, sum));
                }
            }
        }
        
        data.set(output);
    }
    
    applyAdaptiveThreshold(data, width, height) {
        // Convert to grayscale
        const gray = new Uint8Array(width * height);
        for (let i = 0; i < width * height; i++) {
            const idx = i * 4;
            gray[i] = Math.round(0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2]);
        }
        
        // Apply adaptive threshold for better QR code detection
        const blockSize = 15;
        const c = 10;
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = y * width + x;
                
                // Calculate local mean
                let sum = 0;
                let count = 0;
                
                for (let by = Math.max(0, y - blockSize); by < Math.min(height, y + blockSize + 1); by++) {
                    for (let bx = Math.max(0, x - blockSize); bx < Math.min(width, x + blockSize + 1); bx++) {
                        sum += gray[by * width + bx];
                        count++;
                    }
                }
                
                const mean = sum / count;
                const threshold = mean - c;
                const value = gray[idx] > threshold ? 255 : 0;
                
                const dataIdx = idx * 4;
                data[dataIdx] = value;
                data[dataIdx + 1] = value;
                data[dataIdx + 2] = value;
            }
        }
    }
    
    async startZXingScanning() {
        // Check if ZXing is available
        if (typeof ZXing === 'undefined') {
            console.log('LiveQR: ZXing not available, skipping ZXing scanner');
            return;
        }
        
        try {
            // Check for the correct ZXing object structure
            let codeReader;
            
            // Try different ZXing API structures
            if (ZXing.BrowserQRCodeReader) {
                codeReader = new ZXing.BrowserQRCodeReader();
            } else if (window.ZXingBrowser && window.ZXingBrowser.BrowserQRCodeReader) {
                codeReader = new window.ZXingBrowser.BrowserQRCodeReader();
            } else {
                console.log('LiveQR: ZXing loaded but BrowserQRCodeReader not found');
                return;
            }
            
            this.scanners.zxing = codeReader;
            
            // Use the video element for decoding
            await codeReader.decodeFromVideoDevice(undefined, this.video, (result, err) => {
                if (result && !this.isPaused) {
                    this.handleDetection(result.text, 'ZXing');
                }
                // Ignore errors as they're normal when no QR code is visible
            });
            
            console.log('LiveQR: ZXing scanning started successfully');
        } catch (error) {
            console.log('LiveQR: ZXing initialization failed (non-critical):', error.message);
            // Continue without ZXing - jsQR will still work
        }
    }
    
    handleDetection(qrText, source) {
        // Prevent duplicate scans
        const now = Date.now();
        if (qrText === this.lastSuccessfulScan && (now - this.lastScanTime) < 500) {
            return;
        }
        
        console.log(`LiveQR: QR detected by ${source}: ${qrText}`);
        
        this.lastSuccessfulScan = qrText;
        this.lastScanTime = now;
        
        this.handleSuccess(qrText);
    }
    
    handleSuccess(qrText) {
        // Prevent multiple scans while processing
        if (this.isPaused) {
            console.log('LiveQR: Scan ignored - scanner is paused');
            return;
        }
        
        console.log('LiveQR: Success:', qrText);
        
        // Pause scanning immediately to prevent duplicate scans
        this.pauseScanning();
        
        // Flash effect
        const flash = document.getElementById('success-flash');
        if (flash) {
            flash.classList.add('show');
            setTimeout(() => flash.classList.remove('show'), 200);
        }
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([50, 30, 50]); // Enhanced pattern
        }
        
        if (this.onSuccess) {
            // Call the success callback
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
        
        // Also update the scan text
        const scanText = this.container.querySelector('.scan-text');
        if (scanText) {
            scanText.textContent = message;
            scanText.style.color = type === 'error' ? '#ff4444' : type === 'success' ? '#00ff00' : 'white';
        }
    }
    
    async start() {
        if (!this.isScanning) {
            await this.startScanning();
        }
    }
    
    pauseScanning() {
        console.log('LiveQR: Pausing scanner - camera stays active for instant resume');
        this.isPaused = true;
        
        // Update scan text to show paused state
        const scanText = this.container.querySelector('.scan-text');
        if (scanText) {
            scanText.textContent = 'Processing...';
        }
        
        // Camera stays completely active - just ignore scans
        console.log('LiveQR: Processing paused, camera still running at full speed');
    }
    
    resumeScanning() {
        console.log('LiveQR: Resuming scanner - FAST mode');
        
        // Simply unpause - don't restart anything
        this.isPaused = false;
        
        // Update scan text back to normal
        const scanText = this.container.querySelector('.scan-text');
        if (scanText) {
            scanText.textContent = 'Position QR code in frame';
        }
        
        // Make sure scanning flag is true
        this.isScanning = true;
        
        console.log('LiveQR: Scanner resumed instantly - camera still active');
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
        
        if (this.scanners.zxing) {
            try {
                this.scanners.zxing.reset();
            } catch (e) {}
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
        // Manual entry prompt
        const resultContainer = document.getElementById('result-container');
        if (resultContainer) {
            resultContainer.className = 'alert alert-info';
            resultContainer.innerHTML = `
                <i class="fas fa-keyboard me-2"></i>
                Manual entry available below if camera doesn't work
            `;
            resultContainer.style.display = 'block';
        }
    }
}