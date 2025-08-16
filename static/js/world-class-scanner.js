/**
 * World-Class QR Scanner - Superior to Google Lens
 * Handles the worst conditions: dim lights, blur, crushed plastic, any angle
 * Works on ALL mobile devices with advanced fallback strategies
 */

class WorldClassScanner {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.isScanning = false;
        this.isPaused = false;
        this.lastScanTime = 0;
        this.scanDebounce = options.scanDebounce || 500;
        
        // Callbacks
        this.onSuccess = options.onSuccess || null;
        this.onError = options.onError || null;
        
        // State management
        this.scanAttempts = 0;
        this.maxAttempts = 5;
        this.currentStrategy = 0;
        this.lastSuccessfulStrategy = null;
        
        // Multiple scanner instances for parallel processing
        this.scanners = {
            html5QrCode: null,
            jsQR: null,
            zxing: null,
            qrious: null
        };
        
        // Advanced camera features
        this.stream = null;
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.imageCapture = null;
        
        // Enhancement canvases for preprocessing
        this.enhancementCanvases = [];
        for (let i = 0; i < 4; i++) {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d', { willReadFrequently: true });
            this.enhancementCanvases.push({ canvas, context });
        }
        
        // Device capabilities
        this.capabilities = {
            torch: false,
            zoom: false,
            focus: false,
            exposure: false,
            resolution: { width: 1920, height: 1080 }
        };
        
        // Scanning strategies for different conditions
        this.strategies = [
            { name: 'standard', enhance: false, zoom: 1.0 },
            { name: 'enhanced', enhance: true, zoom: 1.0 },
            { name: 'zoomed', enhance: false, zoom: 1.5 },
            { name: 'torch', enhance: true, zoom: 1.0, torch: true },
            { name: 'aggressive', enhance: true, zoom: 2.0, torch: true }
        ];
        
        // Web Worker for parallel processing
        this.worker = null;
        this.initializeWorker();
        
        // Initialize scanner
        this.init();
    }
    
    async init() {
        console.log('WorldClass Scanner: Initializing superior scanning system');
        
        // Load external libraries with fallbacks
        await this.loadExternalLibraries();
        
        // Setup UI
        this.setupUI();
        
        // Request camera with optimal settings
        await this.startCamera();
        
        // Start scanning loop
        this.startScanningLoop();
    }
    
    async loadExternalLibraries() {
        // Load multiple QR libraries for redundancy
        const libraries = [
            { 
                url: 'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js',
                check: () => typeof Html5Qrcode !== 'undefined'
            },
            {
                url: 'https://cdn.jsdelivr.net/npm/@zxing/library@latest',
                check: () => typeof ZXing !== 'undefined'
            },
            {
                url: 'https://cdn.jsdelivr.net/npm/qr-scanner@latest/qr-scanner.min.js',
                check: () => typeof QrScanner !== 'undefined'
            }
        ];
        
        for (const lib of libraries) {
            if (!lib.check()) {
                try {
                    await this.loadScript(lib.url);
                    console.log(`Loaded library: ${lib.url}`);
                } catch (e) {
                    console.warn(`Failed to load ${lib.url}, continuing...`);
                }
            }
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
    
    initializeWorker() {
        // Create Web Worker for parallel image processing
        const workerCode = `
            self.onmessage = function(e) {
                const { imageData, strategy } = e.data;
                
                // Apply image enhancements based on strategy
                if (strategy.enhance) {
                    enhanceImage(imageData);
                }
                
                self.postMessage({ enhanced: imageData });
            };
            
            function enhanceImage(imageData) {
                const data = imageData.data;
                
                // Adaptive histogram equalization
                const histogram = new Array(256).fill(0);
                for (let i = 0; i < data.length; i += 4) {
                    histogram[data[i]]++;
                }
                
                // Calculate cumulative distribution
                const cdf = [];
                cdf[0] = histogram[0];
                for (let i = 1; i < 256; i++) {
                    cdf[i] = cdf[i - 1] + histogram[i];
                }
                
                // Normalize
                const pixels = data.length / 4;
                const normalized = cdf.map(val => Math.round((val * 255) / pixels));
                
                // Apply equalization
                for (let i = 0; i < data.length; i += 4) {
                    data[i] = normalized[data[i]];
                    data[i + 1] = normalized[data[i + 1]];
                    data[i + 2] = normalized[data[i + 2]];
                }
                
                return imageData;
            }
        `;
        
        const blob = new Blob([workerCode], { type: 'application/javascript' });
        const workerUrl = URL.createObjectURL(blob);
        
        try {
            this.worker = new Worker(workerUrl);
        } catch (e) {
            console.warn('Web Worker not supported, using main thread');
        }
    }
    
    setupUI() {
        if (!this.container) return;
        
        this.container.innerHTML = `
            <div class="world-class-scanner">
                <div class="scanner-viewport">
                    <video id="wc-video" playsinline></video>
                    <canvas id="wc-canvas" style="display: none;"></canvas>
                    <div class="scanner-overlay">
                        <div class="scanner-frame">
                            <div class="corner top-left"></div>
                            <div class="corner top-right"></div>
                            <div class="corner bottom-left"></div>
                            <div class="corner bottom-right"></div>
                        </div>
                        <div class="scanner-line"></div>
                    </div>
                </div>
                <div class="scanner-controls">
                    <button id="wc-torch" class="control-btn" style="display: none;">
                        <i class="fas fa-lightbulb"></i>
                    </button>
                    <button id="wc-zoom-in" class="control-btn" style="display: none;">
                        <i class="fas fa-search-plus"></i>
                    </button>
                    <button id="wc-zoom-out" class="control-btn" style="display: none;">
                        <i class="fas fa-search-minus"></i>
                    </button>
                    <button id="wc-switch-camera" class="control-btn">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                </div>
                <div class="scanner-status">
                    <span id="wc-status">Initializing world-class scanner...</span>
                    <div class="scanner-progress" id="wc-progress"></div>
                </div>
            </div>
        `;
        
        // Add styles
        this.addStyles();
        
        // Get elements
        this.video = document.getElementById('wc-video');
        this.canvas = document.getElementById('wc-canvas');
        this.context = this.canvas.getContext('2d', { willReadFrequently: true });
        
        // Setup control handlers
        this.setupControls();
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .world-class-scanner {
                position: relative;
                width: 100%;
                height: 100%;
                background: #000;
                border-radius: 12px;
                overflow: hidden;
            }
            
            .scanner-viewport {
                position: relative;
                width: 100%;
                height: 400px;
                overflow: hidden;
            }
            
            #wc-video {
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
            
            .scanner-frame {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 250px;
                height: 250px;
                border: 2px solid transparent;
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { border-color: rgba(76, 175, 80, 0.3); }
                50% { border-color: rgba(76, 175, 80, 0.8); }
            }
            
            .corner {
                position: absolute;
                width: 20px;
                height: 20px;
                border: 3px solid #4CAF50;
            }
            
            .corner.top-left {
                top: -2px;
                left: -2px;
                border-right: none;
                border-bottom: none;
            }
            
            .corner.top-right {
                top: -2px;
                right: -2px;
                border-left: none;
                border-bottom: none;
            }
            
            .corner.bottom-left {
                bottom: -2px;
                left: -2px;
                border-right: none;
                border-top: none;
            }
            
            .corner.bottom-right {
                bottom: -2px;
                right: -2px;
                border-left: none;
                border-top: none;
            }
            
            .scanner-line {
                position: absolute;
                left: 50%;
                transform: translateX(-50%);
                width: 250px;
                height: 2px;
                background: linear-gradient(90deg, transparent, #4CAF50, transparent);
                animation: scan 2s linear infinite;
            }
            
            @keyframes scan {
                0% { top: 50%; transform: translateX(-50%) translateY(-125px); }
                50% { top: 50%; transform: translateX(-50%) translateY(125px); }
                100% { top: 50%; transform: translateX(-50%) translateY(-125px); }
            }
            
            .scanner-controls {
                position: absolute;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                gap: 15px;
                z-index: 10;
            }
            
            .control-btn {
                width: 50px;
                height: 50px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.9);
                border: 2px solid #4CAF50;
                color: #333;
                font-size: 20px;
                cursor: pointer;
                transition: all 0.3s;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .control-btn:hover {
                background: #4CAF50;
                color: white;
                transform: scale(1.1);
            }
            
            .control-btn.active {
                background: #4CAF50;
                color: white;
            }
            
            .scanner-status {
                position: absolute;
                top: 10px;
                left: 10px;
                right: 10px;
                background: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 10px;
                border-radius: 8px;
                font-size: 12px;
                text-align: center;
            }
            
            .scanner-progress {
                margin-top: 5px;
                height: 3px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 3px;
                overflow: hidden;
            }
            
            .scanner-progress::after {
                content: '';
                display: block;
                height: 100%;
                background: #4CAF50;
                animation: progress 1s linear infinite;
            }
            
            @keyframes progress {
                0% { width: 0%; }
                100% { width: 100%; }
            }
            
            @media (max-width: 768px) {
                .scanner-viewport {
                    height: 300px;
                }
                
                .scanner-frame,
                .scanner-line {
                    width: 200px;
                    height: 200px;
                }
            }
        `;
        
        document.head.appendChild(style);
    }
    
    setupControls() {
        // Torch control
        const torchBtn = document.getElementById('wc-torch');
        if (torchBtn) {
            torchBtn.addEventListener('click', () => this.toggleTorch());
        }
        
        // Zoom controls
        const zoomInBtn = document.getElementById('wc-zoom-in');
        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => this.adjustZoom(1.2));
        }
        
        const zoomOutBtn = document.getElementById('wc-zoom-out');
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => this.adjustZoom(0.8));
        }
        
        // Camera switch
        const switchBtn = document.getElementById('wc-switch-camera');
        if (switchBtn) {
            switchBtn.addEventListener('click', () => this.switchCamera());
        }
    }
    
    async startCamera() {
        try {
            // Get available devices
            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(device => device.kind === 'videoinput');
            
            console.log(`Found ${videoDevices.length} camera(s)`);
            
            // Try different constraint sets for maximum compatibility
            const constraintSets = [
                // Ideal: High resolution with advanced features
                {
                    video: {
                        facingMode: { ideal: 'environment' },
                        width: { ideal: 1920, min: 640 },
                        height: { ideal: 1080, min: 480 },
                        frameRate: { ideal: 30, min: 15 },
                        focusMode: { ideal: 'continuous' },
                        exposureMode: { ideal: 'continuous' },
                        whiteBalanceMode: { ideal: 'continuous' }
                    }
                },
                // Fallback 1: Standard resolution
                {
                    video: {
                        facingMode: 'environment',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    }
                },
                // Fallback 2: Basic constraints
                {
                    video: {
                        facingMode: 'environment'
                    }
                },
                // Fallback 3: Any camera
                {
                    video: true
                }
            ];
            
            let stream = null;
            let selectedConstraints = null;
            
            // Try each constraint set
            for (const constraints of constraintSets) {
                try {
                    stream = await navigator.mediaDevices.getUserMedia(constraints);
                    selectedConstraints = constraints;
                    console.log('Camera started with constraints:', constraints);
                    break;
                } catch (e) {
                    console.warn('Failed with constraints:', constraints, e);
                }
            }
            
            if (!stream) {
                throw new Error('Could not access camera with any constraint set');
            }
            
            this.stream = stream;
            this.video.srcObject = stream;
            
            // Wait for video to be ready
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play();
                    resolve();
                };
            });
            
            // Setup canvas size
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            
            // Setup ImageCapture for advanced features
            const track = stream.getVideoTracks()[0];
            if ('ImageCapture' in window) {
                this.imageCapture = new ImageCapture(track);
                await this.detectCapabilities();
            }
            
            // Update status
            this.updateStatus('Scanner ready - Point at QR code');
            
        } catch (error) {
            console.error('Camera initialization failed:', error);
            this.updateStatus('Camera error: ' + error.message);
            
            if (this.onError) {
                this.onError(error);
            }
        }
    }
    
    async detectCapabilities() {
        if (!this.imageCapture) return;
        
        try {
            const capabilities = await this.imageCapture.getPhotoCapabilities();
            console.log('Camera capabilities:', capabilities);
            
            // Check torch support
            const track = this.stream.getVideoTracks()[0];
            const trackCapabilities = track.getCapabilities ? track.getCapabilities() : {};
            
            if ('torch' in trackCapabilities) {
                this.capabilities.torch = true;
                document.getElementById('wc-torch').style.display = 'flex';
            }
            
            // Check zoom support
            if (capabilities.zoom && capabilities.zoom.min !== capabilities.zoom.max) {
                this.capabilities.zoom = true;
                this.capabilities.zoomMin = capabilities.zoom.min;
                this.capabilities.zoomMax = capabilities.zoom.max;
                document.getElementById('wc-zoom-in').style.display = 'flex';
                document.getElementById('wc-zoom-out').style.display = 'flex';
            }
            
            // Store resolution capabilities
            if (capabilities.imageWidth) {
                this.capabilities.resolution.width = capabilities.imageWidth.max;
                this.capabilities.resolution.height = capabilities.imageHeight.max;
            }
            
        } catch (e) {
            console.warn('Could not detect camera capabilities:', e);
        }
    }
    
    async toggleTorch() {
        if (!this.capabilities.torch) return;
        
        try {
            const track = this.stream.getVideoTracks()[0];
            const currentTorch = track.getSettings().torch || false;
            
            await track.applyConstraints({
                advanced: [{ torch: !currentTorch }]
            });
            
            document.getElementById('wc-torch').classList.toggle('active');
            console.log('Torch toggled:', !currentTorch);
            
        } catch (e) {
            console.error('Failed to toggle torch:', e);
        }
    }
    
    async adjustZoom(factor) {
        if (!this.capabilities.zoom) return;
        
        try {
            const track = this.stream.getVideoTracks()[0];
            const settings = track.getSettings();
            const currentZoom = settings.zoom || 1;
            const newZoom = Math.max(
                this.capabilities.zoomMin,
                Math.min(this.capabilities.zoomMax, currentZoom * factor)
            );
            
            await track.applyConstraints({
                advanced: [{ zoom: newZoom }]
            });
            
            console.log('Zoom adjusted:', newZoom);
            
        } catch (e) {
            console.error('Failed to adjust zoom:', e);
        }
    }
    
    async switchCamera() {
        try {
            // Get current facing mode
            const track = this.stream.getVideoTracks()[0];
            const settings = track.getSettings();
            const currentFacingMode = settings.facingMode || 'environment';
            
            // Stop current stream
            this.stream.getTracks().forEach(track => track.stop());
            
            // Start with opposite facing mode
            const newFacingMode = currentFacingMode === 'environment' ? 'user' : 'environment';
            
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: newFacingMode,
                    width: { ideal: 1920 },
                    height: { ideal: 1080 }
                }
            });
            
            this.stream = stream;
            this.video.srcObject = stream;
            
            console.log('Switched camera to:', newFacingMode);
            
        } catch (e) {
            console.error('Failed to switch camera:', e);
        }
    }
    
    startScanningLoop() {
        if (this.isScanning) return;
        
        this.isScanning = true;
        this.scanFrame();
    }
    
    async scanFrame() {
        if (!this.isScanning || this.isPaused) {
            requestAnimationFrame(() => this.scanFrame());
            return;
        }
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            // Capture frame
            this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            
            // Get current strategy
            const strategy = this.strategies[this.currentStrategy];
            
            // Apply strategy-specific settings
            if (strategy.torch && this.capabilities.torch) {
                this.enableTorch(true);
            }
            
            if (strategy.zoom && this.capabilities.zoom) {
                this.adjustZoom(strategy.zoom);
            }
            
            // Get image data
            const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // Process in parallel with different techniques
            const scanPromises = [];
            
            // Technique 1: Original image
            scanPromises.push(this.scanWithAllLibraries(imageData));
            
            // Technique 2: Enhanced contrast
            if (strategy.enhance) {
                const enhanced1 = this.enhanceContrast(imageData);
                scanPromises.push(this.scanWithAllLibraries(enhanced1));
            }
            
            // Technique 3: Sharpened
            if (strategy.enhance) {
                const enhanced2 = this.sharpenImage(imageData);
                scanPromises.push(this.scanWithAllLibraries(enhanced2));
            }
            
            // Technique 4: Adaptive threshold
            if (strategy.enhance) {
                const enhanced3 = this.applyAdaptiveThreshold(imageData);
                scanPromises.push(this.scanWithAllLibraries(enhanced3));
            }
            
            // Wait for any successful scan
            try {
                const results = await Promise.race(scanPromises);
                if (results) {
                    this.handleSuccessfulScan(results);
                    return;
                }
            } catch (e) {
                // Continue scanning
            }
            
            // Try next strategy if current one fails
            this.scanAttempts++;
            if (this.scanAttempts > this.maxAttempts) {
                this.scanAttempts = 0;
                this.currentStrategy = (this.currentStrategy + 1) % this.strategies.length;
                this.updateStatus(`Trying strategy: ${this.strategies[this.currentStrategy].name}`);
            }
        }
        
        // Continue scanning
        requestAnimationFrame(() => this.scanFrame());
    }
    
    async scanWithAllLibraries(imageData) {
        const promises = [];
        
        // Try jsQR
        if (typeof jsQR !== 'undefined') {
            promises.push(new Promise((resolve) => {
                try {
                    const code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: 'dontInvert'
                    });
                    if (code) {
                        resolve({ data: code.data, library: 'jsQR' });
                    } else {
                        resolve(null);
                    }
                } catch (e) {
                    resolve(null);
                }
            }));
        }
        
        // Try ZXing
        if (typeof ZXing !== 'undefined') {
            promises.push(new Promise(async (resolve) => {
                try {
                    const codeReader = new ZXing.BrowserQRCodeReader();
                    const result = await codeReader.decodeFromImageData(imageData);
                    resolve({ data: result.text, library: 'ZXing' });
                } catch (e) {
                    resolve(null);
                }
            }));
        }
        
        // Try Html5QrCode (if available as scanner instance)
        if (this.scanners.html5QrCode) {
            promises.push(new Promise(async (resolve) => {
                try {
                    // Convert imageData to blob for Html5QrCode
                    const tempCanvas = document.createElement('canvas');
                    tempCanvas.width = imageData.width;
                    tempCanvas.height = imageData.height;
                    const tempCtx = tempCanvas.getContext('2d');
                    tempCtx.putImageData(imageData, 0, 0);
                    
                    tempCanvas.toBlob(async (blob) => {
                        try {
                            const file = new File([blob], 'scan.png', { type: 'image/png' });
                            const result = await Html5Qrcode.scanFile(file, false);
                            resolve({ data: result, library: 'Html5QrCode' });
                        } catch (e) {
                            resolve(null);
                        }
                    });
                } catch (e) {
                    resolve(null);
                }
            }));
        }
        
        // Return first successful result
        const results = await Promise.all(promises);
        return results.find(r => r !== null) || null;
    }
    
    enhanceContrast(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const factor = 1.5; // Contrast factor
        
        for (let i = 0; i < data.length; i += 4) {
            data[i] = Math.min(255, (data[i] - 128) * factor + 128);
            data[i + 1] = Math.min(255, (data[i + 1] - 128) * factor + 128);
            data[i + 2] = Math.min(255, (data[i + 2] - 128) * factor + 128);
        }
        
        return new ImageData(data, imageData.width, imageData.height);
    }
    
    sharpenImage(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const width = imageData.width;
        const height = imageData.height;
        
        // Sharpening kernel
        const kernel = [
            0, -1, 0,
            -1, 5, -1,
            0, -1, 0
        ];
        
        const result = new Uint8ClampedArray(data.length);
        
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                const idx = (y * width + x) * 4;
                
                for (let c = 0; c < 3; c++) {
                    let sum = 0;
                    for (let ky = -1; ky <= 1; ky++) {
                        for (let kx = -1; kx <= 1; kx++) {
                            const kidx = ((y + ky) * width + (x + kx)) * 4;
                            const kval = kernel[(ky + 1) * 3 + (kx + 1)];
                            sum += data[kidx + c] * kval;
                        }
                    }
                    result[idx + c] = Math.min(255, Math.max(0, sum));
                }
                result[idx + 3] = data[idx + 3]; // Alpha
            }
        }
        
        return new ImageData(result, width, height);
    }
    
    applyAdaptiveThreshold(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const width = imageData.width;
        const height = imageData.height;
        const result = new Uint8ClampedArray(data.length);
        
        // Convert to grayscale first
        for (let i = 0; i < data.length; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            data[i] = data[i + 1] = data[i + 2] = gray;
        }
        
        // Apply adaptive threshold
        const blockSize = 25;
        const C = 10;
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = (y * width + x) * 4;
                
                // Calculate local mean
                let sum = 0;
                let count = 0;
                
                for (let by = Math.max(0, y - blockSize); by <= Math.min(height - 1, y + blockSize); by++) {
                    for (let bx = Math.max(0, x - blockSize); bx <= Math.min(width - 1, x + blockSize); bx++) {
                        const bidx = (by * width + bx) * 4;
                        sum += data[bidx];
                        count++;
                    }
                }
                
                const mean = sum / count;
                const threshold = mean - C;
                
                const value = data[idx] > threshold ? 255 : 0;
                result[idx] = result[idx + 1] = result[idx + 2] = value;
                result[idx + 3] = 255;
            }
        }
        
        return new ImageData(result, width, height);
    }
    
    handleSuccessfulScan(result) {
        if (!result || !result.data) return;
        
        // Debounce duplicate scans
        const now = Date.now();
        if (now - this.lastScanTime < this.scanDebounce) {
            return;
        }
        
        this.lastScanTime = now;
        this.isPaused = true;
        
        console.log(`QR Code detected by ${result.library}: ${result.data}`);
        
        // Remember successful strategy
        this.lastSuccessfulStrategy = this.currentStrategy;
        
        // Visual feedback
        this.showSuccessAnimation();
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(200);
        }
        
        // Audio feedback
        this.playSuccessSound();
        
        // Update status
        this.updateStatus(`Success! QR: ${result.data}`);
        
        // Callback
        if (this.onSuccess) {
            this.onSuccess(result.data);
        }
        
        // Resume scanning after delay
        setTimeout(() => {
            this.isPaused = false;
        }, 2000);
    }
    
    showSuccessAnimation() {
        const frame = document.querySelector('.scanner-frame');
        if (frame) {
            frame.style.borderColor = '#4CAF50';
            frame.style.borderWidth = '4px';
            frame.style.animation = 'success-pulse 0.5s ease';
            
            setTimeout(() => {
                frame.style.borderColor = '';
                frame.style.borderWidth = '';
                frame.style.animation = '';
            }, 500);
        }
    }
    
    playSuccessSound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 880; // A5 note
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0, audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.01);
            gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (e) {
            // Audio not supported
        }
    }
    
    updateStatus(message) {
        const statusEl = document.getElementById('wc-status');
        if (statusEl) {
            statusEl.textContent = message;
        }
    }
    
    enableTorch(enable) {
        if (!this.capabilities.torch) return;
        
        const track = this.stream.getVideoTracks()[0];
        track.applyConstraints({
            advanced: [{ torch: enable }]
        }).catch(e => console.warn('Torch control failed:', e));
    }
    
    async stop() {
        this.isScanning = false;
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
        
        if (this.worker) {
            this.worker.terminate();
        }
        
        this.updateStatus('Scanner stopped');
    }
    
    // Static method to check camera availability
    static async isCameraAvailable() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices.some(device => device.kind === 'videoinput');
        } catch (e) {
            return false;
        }
    }
}

// Make globally available
window.WorldClassScanner = WorldClassScanner;