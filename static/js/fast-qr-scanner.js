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
        
        // Balanced optimizations for accuracy and speed
        this.targetWidth = 1280;  // Higher resolution for better detection
        this.targetHeight = 720;
        this.scanRegion = 0.7;   // Larger scan region
        this.frameCount = 0;
        this.fpsFrames = [];
        this.torchSupported = false;
        
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
                    <button id="torch-btn" class="control-btn" title="Flashlight" style="display:none;">💡</button>
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
            console.log('FastQR: Starting camera initialization...');
            
            // Use camera permission helper if available
            if (window.cameraPermissionHelper) {
                this.showStatus('Requesting camera access...', 'info');
                this.cameraStream = await window.cameraPermissionHelper.requestCameraAccess();
            } else {
                // Fallback to direct camera access
                console.log('FastQR: Using fallback camera access');
                this.cameraStream = await this.fallbackCameraAccess();
            }
            
            this.video.srcObject = this.cameraStream;
            
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play().then(resolve);
                };
            });
            
            // Apply comprehensive camera optimizations
            const track = this.cameraStream.getVideoTracks()[0];
            if (track) {
                const capabilities = track.getCapabilities ? track.getCapabilities() : {};
                console.log('FastQR: Camera capabilities:', capabilities);
                
                // Multiple constraint attempts for better compatibility
                const constraintSets = [
                    // High quality settings for better detection
                    {
                        advanced: [
                            { focusMode: 'continuous' },
                            { focusDistance: 0.15 },  // Closer focus for torch
                            { exposureMode: 'continuous' },
                            { exposureCompensation: -1 },  // Prevent overexposure
                            { whiteBalanceMode: 'continuous' },
                            { iso: 100 },  // Lower ISO for torch
                            { brightness: 100 },  // Reduced brightness
                            { contrast: 140 },  // Higher contrast
                            { saturation: 100 },
                            { sharpness: 140 }  // Better edge detection
                        ]
                    },
                    // Standard settings
                    {
                        focusMode: 'continuous',
                        exposureMode: 'continuous',
                        whiteBalanceMode: 'continuous'
                    },
                    // Minimal fallback
                    { focusMode: 'continuous' }
                ];
                
                for (const constraints of constraintSets) {
                    try {
                        await track.applyConstraints(constraints);
                        console.log('FastQR: Applied constraints:', constraints);
                        break;
                    } catch (e) {
                        console.log('FastQR: Constraint failed, trying next');
                    }
                }
                
                // Check torch availability
                if (capabilities.torch) {
                    this.torchSupported = true;
                    const torchBtn = document.getElementById('torch-btn');
                    if (torchBtn) {
                        torchBtn.style.display = 'block';
                    }
                }
            }
            
            this.isScanning = true;
            this.startScanning();
            this.showStatus('Camera active! Point at QR code', 'success');
            
        } catch (error) {
            console.error('FastQR: Camera failed:', error);
            
            // Provide specific, actionable error messages
            let userMessage = error.message || 'Camera error. Please try again.';
            
            // Clean up emojis and technical details for user display
            if (error.message.includes('permission denied') || error.message.includes('Permission denied')) {
                userMessage = 'Camera access blocked. Click the camera icon in your browser address bar and allow access.';
            } else if (error.message.includes('No camera found')) {
                userMessage = 'No camera detected. Please check your camera connection.';
            } else if (error.message.includes('already in use')) {
                userMessage = 'Camera is being used by another app. Please close other camera apps and try again.';
            } else if (error.message.includes('not supported')) {
                userMessage = 'Camera not supported by this browser. Please use Chrome, Firefox, or Safari.';
            }
            
            this.showStatus(userMessage, 'error');
            throw error; // Re-throw to be caught by caller
        }
    }
    
    // Fallback camera access method
    async fallbackCameraAccess() {
        const constraintLevels = [
            {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 640, max: 1280 },
                    height: { ideal: 480, max: 720 }
                },
                audio: false
            },
            {
                video: { facingMode: 'environment' },
                audio: false
            },
            {
                video: true,
                audio: false
            }
        ];

        for (let i = 0; i < constraintLevels.length; i++) {
            try {
                return await navigator.mediaDevices.getUserMedia(constraintLevels[i]);
            } catch (error) {
                if (i === constraintLevels.length - 1) throw error;
                continue;
            }
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
                // Update canvas size if needed
                if (this.canvas.width !== this.video.videoWidth) {
                    this.canvas.width = Math.min(this.video.videoWidth, 1280);
                    this.canvas.height = Math.min(this.video.videoHeight, 720);
                }
                
                if (this.canvas.width > 0 && this.canvas.height > 0) {
                    // Draw video frame
                    this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                    
                    let detected = false;
                    
                    // Strategy 1: Try raw image first (better for torch)
                    if (!detected) {
                        const fullData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
                        
                        // Direct scan without processing
                        let code = jsQR(fullData.data, fullData.width, fullData.height, {
                            inversionAttempts: 'attemptBoth'  // Try both normal and inverted
                        });
                        
                        if (code && code.data) {
                            this.handleSuccess(code.data);
                            detected = true;
                        } else if (this.frameCount % 2 === 0) {
                            // Only enhance if direct scan fails
                            const enhanced = this.enhanceForTorch(fullData);
                            code = jsQR(enhanced.data, enhanced.width, enhanced.height, {
                                inversionAttempts: 'dontInvert'  // Already processed
                            });
                            
                            if (code && code.data) {
                                this.handleSuccess(code.data);
                                detected = true;
                            }
                        }
                    }
                    
                    // Strategy 2: Center region with adaptive processing
                    if (!detected) {
                        const regionSize = Math.floor(this.canvas.width * this.scanRegion);
                        const offsetX = Math.floor((this.canvas.width - regionSize) / 2);
                        const offsetY = Math.floor((this.canvas.height - regionSize) / 2);
                        
                        const regionData = this.context.getImageData(
                            offsetX, offsetY, regionSize, regionSize
                        );
                        
                        // Try raw first
                        let code = jsQR(regionData.data, regionData.width, regionData.height, {
                            inversionAttempts: 'attemptBoth'  // Try both
                        });
                        
                        if (!code || !code.data) {
                            // Apply adaptive thresholding only if needed
                            this.applyAdaptiveThreshold(regionData);
                            code = jsQR(regionData.data, regionData.width, regionData.height, {
                                inversionAttempts: 'dontInvert'  // Already processed
                            });
                        }
                        
                        if (code && code.data) {
                            this.handleSuccess(code.data);
                            detected = true;
                        }
                    }
                    
                    // Strategy 3: Grid scan for multiple QR codes (every 5 frames)
                    if (!detected && this.frameCount % 5 === 0) {
                        const gridSize = 3;  // 3x3 grid
                        const cellWidth = Math.floor(this.canvas.width / gridSize);
                        const cellHeight = Math.floor(this.canvas.height / gridSize);
                        
                        for (let row = 0; row < gridSize && !detected; row++) {
                            for (let col = 0; col < gridSize && !detected; col++) {
                                const x = col * cellWidth;
                                const y = row * cellHeight;
                                
                                const cellData = this.context.getImageData(
                                    x, y, cellWidth, cellHeight
                                );
                                
                                const code = jsQR(cellData.data, cellData.width, cellData.height, {
                                    inversionAttempts: 'onlyInvert'  // Try inverted
                                });
                                
                                if (code && code.data) {
                                    this.handleSuccess(code.data);
                                    detected = true;
                                }
                            }
                        }
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
        
        // Adjust exposure with torch
        try {
            if (this.torchEnabled) {
                // Torch ON: Reduce exposure
                await track.applyConstraints({
                    advanced: [
                        { torch: true },
                        { exposureCompensation: -2 },
                        { brightness: 80 },
                        { contrast: 150 }
                    ]
                });
            } else {
                // Torch OFF: Normal exposure
                await track.applyConstraints({
                    advanced: [
                        { torch: false },
                        { exposureCompensation: 0 },
                        { brightness: 128 },
                        { contrast: 130 }
                    ]
                });
            }
            if (torchBtn) torchBtn.classList.toggle('active', this.torchEnabled);
            console.log('FastQR: Torch toggled with exposure adjustment');
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
        // Prevent duplicate scans with reasonable delay
        const now = Date.now();
        if (qrText === this.lastScan && (now - this.lastScanTime) < 500) {
            return;
        }
        
        if (this.isPaused) return;
        
        console.log('FastQR: Success:', qrText);
        
        this.lastScan = qrText;
        this.lastScanTime = now;
        
        // Brief pause for stability
        this.pauseScanning();
        setTimeout(() => this.resumeScanning(), 300);
        
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
    
    // Special processing for torch/flash conditions
    enhanceForTorch(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const len = data.length;
        
        // Check for overexposure
        let brightCount = 0;
        let totalBrightness = 0;
        const pixels = len / 4;
        
        for (let i = 0; i < len; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            totalBrightness += gray;
            if (gray > 200) brightCount++;
        }
        
        const avgBright = totalBrightness / pixels;
        const overexposed = (brightCount / pixels) > 0.25;
        
        if (overexposed) {
            // Compensate for torch overexposure
            for (let i = 0; i < len; i += 4) {
                // Reduce brightness by 40%
                const r = data[i] * 0.6;
                const g = data[i+1] * 0.6;
                const b = data[i+2] * 0.6;
                
                const gray = 0.299 * r + 0.587 * g + 0.114 * b;
                
                // Three-level thresholding for torch
                let value;
                if (gray < 100) value = 0;
                else if (gray > 150) value = 255;
                else value = 128;
                
                data[i] = data[i+1] = data[i+2] = value;
            }
        } else {
            // Simple threshold for normal lighting
            const threshold = avgBright;
            
            for (let i = 0; i < len; i += 4) {
                const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
                const value = gray > threshold ? 255 : 0;
                data[i] = data[i+1] = data[i+2] = value;
            }
        }
        
        return { data, width: imageData.width, height: imageData.height };
    }
    
    // Enhanced image processing for better QR detection
    enhanceForDetection(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const len = data.length;
        
        // Calculate histogram for auto-levels
        const histogram = new Array(256).fill(0);
        let totalPixels = 0;
        
        for (let i = 0; i < len; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            histogram[Math.floor(gray)]++;
            totalPixels++;
        }
        
        // Find effective range (ignore outliers)
        let cumulative = 0;
        let minLevel = 0, maxLevel = 255;
        
        for (let i = 0; i < 256; i++) {
            cumulative += histogram[i];
            if (cumulative > totalPixels * 0.02) {  // Skip bottom 2%
                minLevel = i;
                break;
            }
        }
        
        cumulative = 0;
        for (let i = 255; i >= 0; i--) {
            cumulative += histogram[i];
            if (cumulative > totalPixels * 0.02) {  // Skip top 2%
                maxLevel = i;
                break;
            }
        }
        
        // Apply auto-levels and enhanced contrast
        const range = maxLevel - minLevel || 1;
        const scale = 255 / range;
        
        for (let i = 0; i < len; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            
            // Auto-levels
            let adjusted = (gray - minLevel) * scale;
            
            // Boost contrast for QR codes
            adjusted = adjusted > 127 ? 
                127 + (adjusted - 127) * 1.2 :  // Brighten lights
                adjusted * 0.8;  // Darken darks
            
            // Apply sharpening
            adjusted = adjusted * 1.15 - 0.075 * 255;
            
            // Clamp and apply
            adjusted = Math.max(0, Math.min(255, adjusted));
            data[i] = data[i+1] = data[i+2] = adjusted;
        }
        
        return { data, width: imageData.width, height: imageData.height };
    }
    
    // Adaptive threshold for varying lighting
    applyAdaptiveThreshold(imageData) {
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        
        // Create grayscale copy
        const gray = new Uint8Array(width * height);
        for (let i = 0, j = 0; i < data.length; i += 4, j++) {
            gray[j] = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
        }
        
        // Apply adaptive threshold
        const blockSize = 15;  // Size of local area
        const c = 10;  // Constant subtracted from mean
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = y * width + x;
                
                // Calculate local mean
                let sum = 0, count = 0;
                const halfBlock = Math.floor(blockSize / 2);
                
                for (let dy = -halfBlock; dy <= halfBlock; dy++) {
                    for (let dx = -halfBlock; dx <= halfBlock; dx++) {
                        const ny = y + dy;
                        const nx = x + dx;
                        
                        if (ny >= 0 && ny < height && nx >= 0 && nx < width) {
                            sum += gray[ny * width + nx];
                            count++;
                        }
                    }
                }
                
                const threshold = (sum / count) - c;
                const value = gray[idx] > threshold ? 255 : 0;
                
                // Apply to image data
                const dataIdx = idx * 4;
                data[dataIdx] = data[dataIdx + 1] = data[dataIdx + 2] = value;
            }
        }
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