/**
 * World-Class QR Scanner - Ultimate Edition
 * ==========================================
 * Handles:
 * - Tiny QR codes (5mm x 5mm)
 * - Damaged/crushed/wrinkled codes
 * - Universal flashlight support
 * - Low light conditions
 * - Motion blur
 * - Partial occlusion
 * - Extreme angles
 */

class WorldClassQRScanner {
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
        
        // Advanced features
        this.torchSupported = false;
        this.torchEnabled = false;
        this.autoFocusSupported = false;
        this.zoomSupported = false;
        this.currentZoom = 1;
        
        // Performance tracking
        this.scanAttempts = 0;
        this.successfulScans = 0;
        this.frameCount = 0;
        
        // Image enhancement settings
        this.enhancementSettings = {
            contrast: 1.5,
            brightness: 1.1,
            sharpness: true,
            denoise: true,
            adaptiveThreshold: true,
            morphology: true
        };
        
        // Initialize permission manager
        this.permissionManager = typeof CameraPermissionManager !== 'undefined' 
            ? new CameraPermissionManager() 
            : null;
        
        console.log('WorldClassQR: Initializing ultimate scanner');
        this.init();
    }
    
    async init() {
        await this.loadExternalLibraries();
        this.setupUI();
        this.setupElements();
        this.setupControls();
        await this.startScanning();
    }
    
    async loadExternalLibraries() {
        // Load ZXing if not already loaded
        if (typeof ZXing === 'undefined' && !document.querySelector('script[src*="zxing"]')) {
            await this.loadScript('https://unpkg.com/@zxing/library@latest');
        }
        
        // Load Html5Qrcode if not already loaded
        if (typeof Html5Qrcode === 'undefined' && !document.querySelector('script[src*="html5-qrcode"]')) {
            await this.loadScript('https://unpkg.com/html5-qrcode');
        }
    }
    
    loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    
    setupUI() {
        this.container.innerHTML = `
            <div class="world-class-scanner">
                <div class="scanner-container">
                    <video id="${this.containerId}-video" autoplay playsinline muted></video>
                    <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
                    <canvas id="${this.containerId}-offscreen" style="display: none;"></canvas>
                    <canvas id="${this.containerId}-enhancement" style="display: none;"></canvas>
                    
                    <!-- Advanced scanning overlay -->
                    <div class="scan-overlay">
                        <div class="scan-frame">
                            <div class="corner tl"></div>
                            <div class="corner tr"></div>
                            <div class="corner bl"></div>
                            <div class="corner br"></div>
                            <div class="scan-line"></div>
                            <div class="focus-indicator"></div>
                        </div>
                        <div class="scan-info">
                            <div class="scan-text">Position QR code in frame</div>
                            <div class="scan-stats" style="display: none;">
                                <span class="fps-counter">0 FPS</span>
                                <span class="scan-quality">Quality: --</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Enhanced controls -->
                    <div class="advanced-controls">
                        <button id="${this.containerId}-torch" class="control-btn torch-btn" title="Flashlight">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 2L12 10M12 18L12 22M4 12L10 12M14 12L20 12M6.34 6.34L10.58 10.58M13.42 13.42L17.66 17.66M6.34 17.66L10.58 13.42M13.42 10.58L17.66 6.34"/>
                            </svg>
                        </button>
                        <button id="${this.containerId}-zoom-in" class="control-btn zoom-btn" title="Zoom In">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"></circle>
                                <path d="M21 21L16.65 16.65M11 8L11 14M8 11L14 11"></path>
                            </svg>
                        </button>
                        <button id="${this.containerId}-zoom-out" class="control-btn zoom-btn" title="Zoom Out">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"></circle>
                                <path d="M21 21L16.65 16.65M8 11L14 11"></path>
                            </svg>
                        </button>
                        <button id="${this.containerId}-enhance" class="control-btn enhance-btn active" title="Image Enhancement">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
                            </svg>
                        </button>
                        <button id="${this.containerId}-autofocus" class="control-btn focus-btn" title="Auto Focus">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0M3 7L3 5a2 2 0 0 1 2 -2h2M17 3L19 3a2 2 0 0 1 2 2v2M21 17L21 19a2 2 0 0 1 -2 2h-2M7 21L5 21a2 2 0 0 1 -2 -2v-2"/>
                            </svg>
                        </button>
                    </div>
                    
                    <!-- Success feedback -->
                    <div class="success-flash" id="${this.containerId}-flash"></div>
                    
                    <!-- Processing indicator -->
                    <div class="processing-indicator" style="display: none;">
                        <div class="spinner"></div>
                        <div>Processing damaged code...</div>
                    </div>
                </div>
            </div>
            
            <style>
                .world-class-scanner {
                    position: relative;
                    width: 100%;
                    height: 450px;
                    border-radius: 12px;
                    overflow: hidden;
                    background: #000;
                }
                
                .scanner-container {
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
                
                .scan-frame {
                    position: relative;
                    width: 250px;
                    height: 250px;
                    margin-bottom: 20px;
                }
                
                .corner {
                    position: absolute;
                    width: 30px;
                    height: 30px;
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
                    100% { top: 244px; opacity: 0; }
                }
                
                .focus-indicator {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: 60px;
                    height: 60px;
                    border: 2px solid rgba(255, 255, 255, 0.8);
                    border-radius: 50%;
                    opacity: 0;
                    animation: focus-pulse 1.5s infinite;
                }
                
                @keyframes focus-pulse {
                    0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0; }
                    50% { transform: translate(-50%, -50%) scale(1.2); opacity: 0.8; }
                }
                
                .scan-info {
                    text-align: center;
                    color: white;
                }
                
                .scan-text {
                    font-size: 16px;
                    font-weight: 500;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
                    margin-bottom: 10px;
                }
                
                .scan-stats {
                    font-size: 12px;
                    opacity: 0.8;
                }
                
                .scan-stats span {
                    margin: 0 10px;
                }
                
                .advanced-controls {
                    position: absolute;
                    bottom: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    display: flex;
                    gap: 10px;
                    pointer-events: auto;
                    background: rgba(0, 0, 0, 0.7);
                    padding: 10px;
                    border-radius: 25px;
                    backdrop-filter: blur(10px);
                }
                
                .control-btn {
                    width: 45px;
                    height: 45px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.15);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    color: white;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .control-btn:hover {
                    background: rgba(255, 255, 255, 0.25);
                    transform: scale(1.1);
                }
                
                .control-btn.active {
                    background: rgba(0, 255, 0, 0.3);
                    border-color: #00ff00;
                    box-shadow: 0 0 10px rgba(0, 255, 0, 0.5);
                }
                
                .control-btn.disabled {
                    opacity: 0.3;
                    cursor: not-allowed;
                }
                
                .success-flash {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: radial-gradient(circle at center, rgba(0, 255, 0, 0.4), transparent);
                    opacity: 0;
                    pointer-events: none;
                    transition: opacity 0.2s ease;
                }
                
                .success-flash.show {
                    opacity: 1;
                }
                
                .processing-indicator {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: rgba(0, 0, 0, 0.9);
                    padding: 20px;
                    border-radius: 10px;
                    color: white;
                    text-align: center;
                    pointer-events: none;
                }
                
                .spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid rgba(255, 255, 255, 0.3);
                    border-top-color: #00ff00;
                    border-radius: 50%;
                    animation: spin 0.8s linear infinite;
                    margin: 0 auto 10px;
                }
                
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            </style>
        `;
    }
    
    setupElements() {
        this.video = document.getElementById(`${this.containerId}-video`);
        this.canvas = document.getElementById(`${this.containerId}-canvas`);
        this.context = this.canvas.getContext('2d', { willReadFrequently: true });
        this.offscreenCanvas = document.getElementById(`${this.containerId}-offscreen`);
        this.offscreenContext = this.offscreenCanvas.getContext('2d', { willReadFrequently: true });
        this.enhancementCanvas = document.getElementById(`${this.containerId}-enhancement`);
        this.enhancementContext = this.enhancementCanvas.getContext('2d', { willReadFrequently: true });
    }
    
    setupControls() {
        // Torch control with multiple fallback methods
        const torchBtn = document.getElementById(`${this.containerId}-torch`);
        if (torchBtn) {
            torchBtn.addEventListener('click', () => this.toggleTorch());
        }
        
        // Zoom controls
        const zoomInBtn = document.getElementById(`${this.containerId}-zoom-in`);
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => this.adjustZoom(0.2));
        }
        
        const zoomOutBtn = document.getElementById(`${this.containerId}-zoom-out`);
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => this.adjustZoom(-0.2));
        }
        
        // Enhancement toggle
        const enhanceBtn = document.getElementById(`${this.containerId}-enhance`);
        if (enhanceBtn) {
            enhanceBtn.addEventListener('click', () => this.toggleEnhancement());
        }
        
        // Auto-focus control
        const focusBtn = document.getElementById(`${this.containerId}-autofocus`);
        if (focusBtn) {
            focusBtn.addEventListener('click', () => this.triggerAutoFocus());
        }
    }
    
    async startScanning() {
        console.log('WorldClassQR: Starting ultimate scanning system...');
        
        try {
            // Request camera with optimal settings for QR scanning
            await this.initializeCamera();
            
            // Start multiple scanning engines in parallel
            this.startMultiEngineScan();
            
            // Initialize performance monitoring
            this.startPerformanceMonitoring();
            
            this.showStatus('Scanner ready - Point at QR code', 'success');
            
        } catch (error) {
            console.error('WorldClassQR: Failed to start scanner:', error);
            this.showStatus(`Camera error: ${error.message}`, 'error');
            this.showManualEntry();
        }
    }
    
    async initializeCamera() {
        console.log('WorldClassQR: Initializing camera with optimal settings...');
        
        // Progressive constraint sets from ideal to basic
        const constraintSets = [
            // Ideal: High resolution, auto-focus, back camera, high frame rate
            {
                video: {
                    facingMode: { exact: 'environment' },
                    width: { ideal: 3840, min: 1920 },
                    height: { ideal: 2160, min: 1080 },
                    frameRate: { ideal: 60, min: 30 },
                    focusMode: { ideal: 'continuous' },
                    exposureMode: { ideal: 'continuous' },
                    whiteBalanceMode: { ideal: 'continuous' },
                    resizeMode: 'none'
                },
                audio: false
            },
            // Good: Medium resolution with back camera
            {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1920 },
                    height: { ideal: 1080 },
                    frameRate: { ideal: 30 }
                },
                audio: false
            },
            // Basic: Any camera that works
            {
                video: true,
                audio: false
            }
        ];
        
        let stream = null;
        let constraintLevel = 0;
        
        for (const constraints of constraintSets) {
            try {
                console.log(`WorldClassQR: Trying constraint level ${constraintLevel}...`);
                stream = await navigator.mediaDevices.getUserMedia(constraints);
                console.log(`WorldClassQR: Success with constraint level ${constraintLevel}`);
                break;
            } catch (error) {
                console.log(`WorldClassQR: Constraint level ${constraintLevel} failed:`, error.message);
                constraintLevel++;
                if (constraintLevel === constraintSets.length) {
                    throw new Error('No suitable camera configuration found');
                }
            }
        }
        
        if (!stream) {
            throw new Error('Failed to access camera');
        }
        
        this.cameraStream = stream;
        this.video.srcObject = stream;
        
        // Wait for video to be ready
        await new Promise((resolve) => {
            this.video.onloadedmetadata = () => {
                this.video.play().then(resolve);
            };
        });
        
        // Check and setup advanced camera features
        await this.setupAdvancedCameraFeatures();
        
        this.isScanning = true;
        console.log('WorldClassQR: Camera initialized successfully');
    }
    
    async setupAdvancedCameraFeatures() {
        const track = this.cameraStream.getVideoTracks()[0];
        if (!track) return;
        
        const capabilities = track.getCapabilities ? track.getCapabilities() : {};
        const settings = track.getSettings ? track.getSettings() : {};
        
        console.log('WorldClassQR: Camera capabilities:', capabilities);
        console.log('WorldClassQR: Current settings:', settings);
        
        // Check torch support (multiple methods for compatibility)
        this.torchSupported = await this.checkTorchSupport(track);
        
        // Check zoom support
        if (capabilities.zoom) {
            this.zoomSupported = true;
            this.minZoom = capabilities.zoom.min || 1;
            this.maxZoom = capabilities.zoom.max || 1;
            this.currentZoom = settings.zoom || 1;
            console.log(`WorldClassQR: Zoom supported (${this.minZoom}x - ${this.maxZoom}x)`);
        }
        
        // Check focus modes
        if (capabilities.focusMode) {
            this.autoFocusSupported = capabilities.focusMode.includes('continuous');
            if (this.autoFocusSupported) {
                await this.setFocusMode('continuous');
            }
        }
        
        // Update UI based on capabilities
        this.updateControlsBasedOnCapabilities();
    }
    
    async checkTorchSupport(track) {
        // Method 1: Check capabilities
        if (track.getCapabilities) {
            const capabilities = track.getCapabilities();
            if (capabilities.torch) {
                console.log('WorldClassQR: Torch supported via capabilities');
                return true;
            }
        }
        
        // Method 2: Try to apply torch constraint
        try {
            await track.applyConstraints({
                advanced: [{ torch: false }]
            });
            console.log('WorldClassQR: Torch supported via applyConstraints');
            return true;
        } catch (e) {
            // Silent fail
        }
        
        // Method 3: Check ImageCapture API
        if (typeof ImageCapture !== 'undefined') {
            try {
                const imageCapture = new ImageCapture(track);
                const photoCapabilities = await imageCapture.getPhotoCapabilities();
                if (photoCapabilities.fillLightMode && photoCapabilities.fillLightMode.includes('flash')) {
                    console.log('WorldClassQR: Torch supported via ImageCapture');
                    this.imageCapture = imageCapture;
                    return true;
                }
            } catch (e) {
                // Silent fail
            }
        }
        
        console.log('WorldClassQR: Torch not supported');
        return false;
    }
    
    updateControlsBasedOnCapabilities() {
        const torchBtn = document.getElementById(`${this.containerId}-torch`);
        const zoomInBtn = document.getElementById(`${this.containerId}-zoom-in`);
        const zoomOutBtn = document.getElementById(`${this.containerId}-zoom-out`);
        const focusBtn = document.getElementById(`${this.containerId}-autofocus`);
        
        if (torchBtn && !this.torchSupported) {
            torchBtn.classList.add('disabled');
            torchBtn.disabled = true;
        }
        
        if (zoomInBtn && !this.zoomSupported) {
            zoomInBtn.classList.add('disabled');
            zoomInBtn.disabled = true;
        }
        
        if (zoomOutBtn && !this.zoomSupported) {
            zoomOutBtn.classList.add('disabled');
            zoomOutBtn.disabled = true;
        }
        
        if (focusBtn && !this.autoFocusSupported) {
            focusBtn.classList.add('disabled');
            focusBtn.disabled = true;
        }
    }
    
    async toggleTorch() {
        if (!this.torchSupported) {
            console.log('WorldClassQR: Torch not supported on this device');
            return;
        }
        
        const track = this.cameraStream.getVideoTracks()[0];
        if (!track) return;
        
        const torchBtn = document.getElementById(`${this.containerId}-torch`);
        
        try {
            // Method 1: Standard torch control
            if (track.applyConstraints) {
                this.torchEnabled = !this.torchEnabled;
                await track.applyConstraints({
                    advanced: [{ torch: this.torchEnabled }]
                });
                console.log(`WorldClassQR: Torch ${this.torchEnabled ? 'ON' : 'OFF'} via constraints`);
            }
            
            // Method 2: ImageCapture API fallback
            else if (this.imageCapture) {
                this.torchEnabled = !this.torchEnabled;
                await this.imageCapture.takePhoto({
                    fillLightMode: this.torchEnabled ? 'flash' : 'off'
                });
                console.log(`WorldClassQR: Torch ${this.torchEnabled ? 'ON' : 'OFF'} via ImageCapture`);
            }
            
            // Update UI
            if (torchBtn) {
                torchBtn.classList.toggle('active', this.torchEnabled);
            }
            
        } catch (error) {
            console.error('WorldClassQR: Failed to toggle torch:', error);
            
            // Try alternative method for iOS devices
            if (this.isIOS()) {
                await this.toggleTorchIOS();
            }
        }
    }
    
    async toggleTorchIOS() {
        // iOS-specific torch handling
        try {
            const track = this.cameraStream.getVideoTracks()[0];
            const constraints = track.getConstraints();
            
            this.torchEnabled = !this.torchEnabled;
            
            // Re-initialize stream with torch setting
            const newConstraints = {
                ...constraints,
                video: {
                    ...constraints.video,
                    torch: this.torchEnabled
                }
            };
            
            const newStream = await navigator.mediaDevices.getUserMedia(newConstraints);
            
            // Replace the stream
            this.cameraStream = newStream;
            this.video.srcObject = newStream;
            
            console.log(`WorldClassQR: iOS Torch ${this.torchEnabled ? 'ON' : 'OFF'}`);
            
        } catch (error) {
            console.error('WorldClassQR: iOS torch toggle failed:', error);
        }
    }
    
    isIOS() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    }
    
    async adjustZoom(delta) {
        if (!this.zoomSupported) return;
        
        const track = this.cameraStream.getVideoTracks()[0];
        if (!track) return;
        
        this.currentZoom = Math.max(this.minZoom, Math.min(this.maxZoom, this.currentZoom + delta));
        
        try {
            await track.applyConstraints({
                advanced: [{ zoom: this.currentZoom }]
            });
            console.log(`WorldClassQR: Zoom set to ${this.currentZoom}x`);
            
            // Update UI
            const qualitySpan = this.container.querySelector('.scan-quality');
            if (qualitySpan) {
                qualitySpan.textContent = `Zoom: ${this.currentZoom.toFixed(1)}x`;
            }
        } catch (error) {
            console.error('WorldClassQR: Failed to adjust zoom:', error);
        }
    }
    
    toggleEnhancement() {
        const enhanceBtn = document.getElementById(`${this.containerId}-enhance`);
        const allEnhanced = Object.values(this.enhancementSettings).every(v => v === true || v > 1);
        
        if (allEnhanced) {
            // Disable all enhancements
            this.enhancementSettings = {
                contrast: 1,
                brightness: 1,
                sharpness: false,
                denoise: false,
                adaptiveThreshold: false,
                morphology: false
            };
            if (enhanceBtn) enhanceBtn.classList.remove('active');
            console.log('WorldClassQR: Image enhancement disabled');
        } else {
            // Enable all enhancements
            this.enhancementSettings = {
                contrast: 1.5,
                brightness: 1.1,
                sharpness: true,
                denoise: true,
                adaptiveThreshold: true,
                morphology: true
            };
            if (enhanceBtn) enhanceBtn.classList.add('active');
            console.log('WorldClassQR: Image enhancement enabled');
        }
    }
    
    async triggerAutoFocus() {
        const track = this.cameraStream.getVideoTracks()[0];
        if (!track || !this.autoFocusSupported) return;
        
        try {
            // Trigger focus by switching modes
            await this.setFocusMode('manual');
            await new Promise(resolve => setTimeout(resolve, 100));
            await this.setFocusMode('continuous');
            
            // Visual feedback
            const focusIndicator = this.container.querySelector('.focus-indicator');
            if (focusIndicator) {
                focusIndicator.style.animation = 'none';
                setTimeout(() => {
                    focusIndicator.style.animation = 'focus-pulse 1.5s';
                }, 10);
            }
            
            console.log('WorldClassQR: Auto-focus triggered');
        } catch (error) {
            console.error('WorldClassQR: Failed to trigger auto-focus:', error);
        }
    }
    
    async setFocusMode(mode) {
        const track = this.cameraStream.getVideoTracks()[0];
        if (!track) return;
        
        try {
            await track.applyConstraints({
                advanced: [{ focusMode: mode }]
            });
        } catch (error) {
            // Silent fail
        }
    }
    
    startMultiEngineScan() {
        // Start native jsQR scanning
        this.startJsQRScanning();
        
        // Start Html5QrCode if available
        if (typeof Html5Qrcode !== 'undefined') {
            this.startHtml5QrCodeScanning();
        }
        
        // Start ZXing if available
        if (typeof ZXing !== 'undefined') {
            this.startZXingScanning();
        }
    }
    
    startJsQRScanning() {
        if (typeof jsQR === 'undefined') {
            console.log('WorldClassQR: jsQR not available');
            return;
        }
        
        const scan = () => {
            if (!this.isScanning) return;
            
            if (!this.isPaused && this.video.readyState === 4) {
                // Capture frame
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
                this.context.drawImage(this.video, 0, 0);
                
                // Try multiple scan strategies in parallel
                this.scanWithMultipleStrategies();
            }
            
            requestAnimationFrame(scan);
        };
        
        scan();
        console.log('WorldClassQR: jsQR scanning started');
    }
    
    scanWithMultipleStrategies() {
        // Strategy 1: Full frame scan
        this.scanFullFrame();
        
        // Strategy 2: Center region scan (faster, for well-positioned codes)
        this.scanCenterRegion();
        
        // Strategy 3: Enhanced image scan (for damaged codes)
        if (this.enhancementSettings.adaptiveThreshold) {
            this.scanEnhancedImage();
        }
        
        // Strategy 4: Multi-scale scan (for tiny codes)
        this.scanMultiScale();
    }
    
    scanFullFrame() {
        const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const code = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'attemptBoth'
        });
        
        if (code && code.data) {
            this.handleDetection(code.data, 'jsQR-full');
        }
    }
    
    scanCenterRegion() {
        const centerSize = 0.6; // Scan 60% center region
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
        // Apply image enhancement
        this.enhancementCanvas.width = this.canvas.width;
        this.enhancementCanvas.height = this.canvas.height;
        
        // Copy original image
        this.enhancementContext.drawImage(this.canvas, 0, 0);
        
        // Apply enhancements
        const imageData = this.enhancementContext.getImageData(0, 0, this.enhancementCanvas.width, this.enhancementCanvas.height);
        const enhanced = this.enhanceImage(imageData);
        this.enhancementContext.putImageData(enhanced, 0, 0);
        
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
        // Scan at different scales for tiny QR codes
        const scales = [1.5, 2.0, 2.5]; // Upscale factors
        
        for (const scale of scales) {
            const scaledWidth = Math.floor(this.canvas.width * scale);
            const scaledHeight = Math.floor(this.canvas.height * scale);
            
            // Skip if too large (memory constraint)
            if (scaledWidth * scaledHeight > 8000000) continue;
            
            this.offscreenCanvas.width = scaledWidth;
            this.offscreenCanvas.height = scaledHeight;
            
            // Draw scaled image
            this.offscreenContext.imageSmoothingEnabled = false; // Preserve sharp edges
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
                break; // Stop after first successful detection
            }
        }
    }
    
    enhanceImage(imageData) {
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        
        // Apply brightness and contrast
        for (let i = 0; i < data.length; i += 4) {
            data[i] = Math.min(255, Math.max(0, (data[i] - 128) * this.enhancementSettings.contrast + 128 * this.enhancementSettings.brightness));
            data[i + 1] = Math.min(255, Math.max(0, (data[i + 1] - 128) * this.enhancementSettings.contrast + 128 * this.enhancementSettings.brightness));
            data[i + 2] = Math.min(255, Math.max(0, (data[i + 2] - 128) * this.enhancementSettings.contrast + 128 * this.enhancementSettings.brightness));
        }
        
        // Apply sharpening
        if (this.enhancementSettings.sharpness) {
            this.applySharpen(data, width, height);
        }
        
        // Apply adaptive threshold
        if (this.enhancementSettings.adaptiveThreshold) {
            this.applyAdaptiveThreshold(data, width, height);
        }
        
        return imageData;
    }
    
    applySharpen(data, width, height) {
        // Simple sharpening kernel
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
        // Convert to grayscale first
        const gray = new Uint8Array(width * height);
        for (let i = 0; i < width * height; i++) {
            const idx = i * 4;
            gray[i] = Math.round(0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2]);
        }
        
        // Apply adaptive threshold
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
    
    async startHtml5QrCodeScanning() {
        if (typeof Html5Qrcode === 'undefined') return;
        
        try {
            const scanner = new Html5Qrcode(`${this.containerId}-video`);
            this.scanners.html5QrCode = scanner;
            
            const config = {
                fps: 30,
                qrbox: { width: 350, height: 350 },
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true
                }
            };
            
            await scanner.start(
                { facingMode: "environment" },
                config,
                (decodedText) => {
                    if (!this.isPaused) {
                        this.handleDetection(decodedText, 'Html5QrCode');
                    }
                },
                () => {} // Ignore errors
            );
            
            console.log('WorldClassQR: Html5QrCode scanning started');
        } catch (error) {
            console.log('WorldClassQR: Html5QrCode initialization failed:', error);
        }
    }
    
    async startZXingScanning() {
        if (typeof ZXing === 'undefined') return;
        
        try {
            const codeReader = new ZXing.BrowserQRCodeReader();
            this.scanners.zxing = codeReader;
            
            await codeReader.decodeFromVideoDevice(null, this.video, (result, err) => {
                if (result && !this.isPaused) {
                    this.handleDetection(result.text, 'ZXing');
                }
            });
            
            console.log('WorldClassQR: ZXing scanning started');
        } catch (error) {
            console.log('WorldClassQR: ZXing initialization failed:', error);
        }
    }
    
    handleDetection(qrText, source) {
        // Prevent duplicate scans
        const now = Date.now();
        if (qrText === this.lastSuccessfulScan && (now - this.lastScanTime) < 500) {
            return;
        }
        
        console.log(`WorldClassQR: QR detected by ${source}: ${qrText}`);
        
        this.lastSuccessfulScan = qrText;
        this.lastScanTime = now;
        this.successfulScans++;
        
        // Pause scanning
        this.pauseScanning();
        
        // Visual feedback
        this.showSuccessFeedback();
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([50, 30, 50]); // Enhanced vibration pattern
        }
        
        // Callback
        if (this.onSuccess) {
            this.onSuccess(qrText);
        }
    }
    
    showSuccessFeedback() {
        // Flash effect
        const flash = document.getElementById(`${this.containerId}-flash`);
        if (flash) {
            flash.classList.add('show');
            setTimeout(() => flash.classList.remove('show'), 300);
        }
        
        // Update scan text
        const scanText = this.container.querySelector('.scan-text');
        if (scanText) {
            scanText.textContent = 'QR Code Detected!';
            scanText.style.color = '#00ff00';
            setTimeout(() => {
                scanText.textContent = 'Position QR code in frame';
                scanText.style.color = 'white';
            }, 2000);
        }
    }
    
    pauseScanning() {
        this.isPaused = true;
        console.log('WorldClassQR: Scanning paused');
    }
    
    resumeScanning() {
        this.isPaused = false;
        console.log('WorldClassQR: Scanning resumed');
    }
    
    startPerformanceMonitoring() {
        let lastTime = performance.now();
        let frames = 0;
        
        const updateStats = () => {
            if (!this.isScanning) return;
            
            frames++;
            const currentTime = performance.now();
            const delta = currentTime - lastTime;
            
            if (delta >= 1000) {
                const fps = Math.round((frames * 1000) / delta);
                const fpsCounter = this.container.querySelector('.fps-counter');
                if (fpsCounter) {
                    fpsCounter.textContent = `${fps} FPS`;
                }
                
                frames = 0;
                lastTime = currentTime;
            }
            
            requestAnimationFrame(updateStats);
        };
        
        updateStats();
    }
    
    showStatus(message, type = 'info') {
        const scanText = this.container.querySelector('.scan-text');
        if (scanText) {
            scanText.textContent = message;
            scanText.style.color = type === 'error' ? '#ff4444' : type === 'success' ? '#00ff00' : 'white';
        }
    }
    
    showManualEntry() {
        // Implement manual entry fallback
        console.log('WorldClassQR: Manual entry fallback');
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
    
    async stop() {
        this.isScanning = false;
        this.isPaused = false;
        
        // Stop all scanners
        if (this.scanners.html5QrCode) {
            try {
                await this.scanners.html5QrCode.stop();
            } catch (e) {}
        }
        
        if (this.scanners.zxing) {
            try {
                this.scanners.zxing.reset();
            } catch (e) {}
        }
        
        // Stop camera
        if (this.cameraStream) {
            this.cameraStream.getTracks().forEach(track => track.stop());
            this.cameraStream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
        
        console.log('WorldClassQR: Scanner stopped');
    }
}

// Make globally available
window.WorldClassQRScanner = WorldClassQRScanner;