// Agricultural QR Scanner - Ultra-fast detection for agricultural supply chain packets
// Optimized for high-density QR codes on plastic packaging with auto-torch enabled

class InstantDetectionScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = null;
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.scanActive = false;
        this.lastScanTime = 0;
        this.lastScanData = null;
        this.scanRegion = null;
        this.torchEnabled = false;
        this.torchSupported = false;
        this.track = null;
        
        // Agricultural packet optimized settings
        this.SCAN_INTERVAL = 16; // 60 FPS scanning
        this.DUPLICATE_TIMEOUT = 200; // 200ms duplicate prevention for rapid scanning
        this.VIDEO_WIDTH = 1280; // Higher resolution for dense QR codes
        this.VIDEO_HEIGHT = 720;
        this.REGION_SIZE = 0.8; // Larger scan region for agricultural packets
        this.MAX_PROCESS_TIME = 10; // Max 10ms per frame processing
        
        // Performance monitoring
        this.frameCount = 0;
        this.lastFpsUpdate = Date.now();
        this.currentFps = 0;
        
        // Initialize immediately
        this.init();
    }
    
    async init() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            console.error('Container not found');
            return;
        }
        
        // Clear any existing content
        this.container.innerHTML = '';
        
        // Create ultra-minimal UI
        this.createMinimalUI();
        
        // Start camera immediately
        await this.startCamera();
    }
    
    createMinimalUI() {
        // Create scanner container with absolute positioning
        const scannerDiv = document.createElement('div');
        scannerDiv.className = 'instant-scanner-container';
        scannerDiv.style.cssText = `
            position: relative;
            width: 100%;
            max-width: 500px;
            margin: 0 auto;
            background: #000;
            border-radius: 12px;
            overflow: hidden;
        `;
        
        // Create video element
        this.video = document.createElement('video');
        this.video.style.cssText = `
            width: 100%;
            height: 200px;
            display: block;
            object-fit: cover;
        `;
        this.video.playsInline = true;
        this.video.muted = true;
        this.video.autoplay = true;
        
        // Create canvas for processing (hidden)
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.VIDEO_WIDTH;
        this.canvas.height = this.VIDEO_HEIGHT;
        this.canvas.style.display = 'none';
        this.context = this.canvas.getContext('2d', {
            willReadFrequently: true,
            alpha: false
        });
        
        // Create scanning overlay with guide box
        const overlay = document.createElement('div');
        overlay.className = 'scanner-overlay';
        overlay.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
        `;
        
        // Create center guide box
        const guideBox = document.createElement('div');
        guideBox.className = 'guide-box';
        guideBox.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: ${this.REGION_SIZE * 100}%;
            height: ${this.REGION_SIZE * 100}%;
            border: 3px solid #4CAF50;
            border-radius: 12px;
            box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
            animation: pulse 1.5s infinite;
        `;
        
        // Create scanning line animation
        const scanLine = document.createElement('div');
        scanLine.className = 'scan-line';
        scanLine.style.cssText = `
            position: absolute;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, transparent, #4CAF50, transparent);
            animation: scan 1.5s linear infinite;
            filter: drop-shadow(0 0 3px #4CAF50);
        `;
        
        // Create status indicator
        const statusDiv = document.createElement('div');
        statusDiv.id = 'scan-status';
        statusDiv.className = 'scan-status';
        statusDiv.style.cssText = `
            position: absolute;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.8);
            color: #4CAF50;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            z-index: 10;
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        statusDiv.innerHTML = `
            <span class="status-dot" style="
                width: 8px;
                height: 8px;
                background: #4CAF50;
                border-radius: 50%;
                animation: blink 1s infinite;
            "></span>
            <span>Ready to scan</span>
        `;
        
        // Create FPS counter (for debugging)
        const fpsDiv = document.createElement('div');
        fpsDiv.id = 'fps-counter';
        fpsDiv.style.cssText = `
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: #4CAF50;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
            z-index: 10;
        `;
        
        // Create agricultural torch indicator (shows auto-enabled status)
        const torchBtn = document.createElement('div');
        torchBtn.id = 'torch-btn';
        torchBtn.style.cssText = `
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(255, 235, 59, 0.8);
            border: 2px solid #FFD700;
            color: #000;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10;
            cursor: pointer;
        `;
        torchBtn.innerHTML = '<i class="fas fa-lightbulb" style="color: #FF8F00;"></i>';
        torchBtn.onclick = () => this.toggleTorch();
        torchBtn.title = 'Agricultural Torch (Auto-Enabled)';
        
        // Add CSS animations
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.8; }
            }
            @keyframes scan {
                0% { top: 0%; }
                100% { top: 100%; }
            }
            @keyframes blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.3; }
            }
        `;
        document.head.appendChild(style);
        
        // Assemble UI
        guideBox.appendChild(scanLine);
        overlay.appendChild(guideBox);
        scannerDiv.appendChild(this.video);
        scannerDiv.appendChild(this.canvas);
        scannerDiv.appendChild(overlay);
        scannerDiv.appendChild(statusDiv);
        scannerDiv.appendChild(fpsDiv);
        scannerDiv.appendChild(torchBtn);
        this.container.appendChild(scannerDiv);
    }
    
    async startCamera() {
        try {
            this.updateStatus('Initializing camera...', '#FFC107');
            console.log('Requesting camera access...');
            
            // Request camera with agricultural packet optimized constraints
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: this.VIDEO_WIDTH },
                    height: { ideal: this.VIDEO_HEIGHT },
                    frameRate: { ideal: 60, min: 30 }, // High frame rate
                    focusMode: 'continuous',
                    exposureMode: 'continuous',
                    torch: true // Request torch to be on by default
                }
            };
            
            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = stream;
            console.log('🌾 Agricultural scanner camera stream obtained');
            
            // Store track for torch control
            this.track = stream.getVideoTracks()[0];
            console.log('Video track:', this.track);
            
            // Setup torch for agricultural scanning
            await this.setupAgriculturalTorch();
            
            // Apply agricultural camera optimizations
            await this.optimizeCameraForAgriculture();
            
            // Wait for video to be ready
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    console.log('Video metadata loaded, dimensions:', this.video.videoWidth, 'x', this.video.videoHeight);
                    this.video.play();
                    resolve();
                };
            });
            
            // Use actual video dimensions for region calculation with safety checks
            const actualWidth = (this.video && this.video.videoWidth) ? this.video.videoWidth : this.VIDEO_WIDTH;
            const actualHeight = (this.video && this.video.videoHeight) ? this.video.videoHeight : this.VIDEO_HEIGHT;
            
            // Update canvas size to match video
            this.canvas.width = actualWidth;
            this.canvas.height = actualHeight;
            
            // Calculate scan region (center 60% of frame)
            const regionOffset = (1 - this.REGION_SIZE) / 2;
            this.scanRegion = {
                x: Math.floor(actualWidth * regionOffset),
                y: Math.floor(actualHeight * regionOffset),
                width: Math.floor(actualWidth * this.REGION_SIZE),
                height: Math.floor(actualHeight * this.REGION_SIZE)
            };
            
            console.log('Scan region:', this.scanRegion);
            
            // Start scanning immediately
            this.scanActive = true;
            this.updateStatus('Scanning...', '#4CAF50');
            this.startScanning();
            
        } catch (error) {
            console.error('Camera error:', error);
            this.updateStatus(`Camera error: ${error.message}`, '#F44336');
        }
    }
    
    startScanning() {
        if (!this.scanActive) return;
        
        const processFrame = () => {
            if (!this.scanActive) return;
            
            const startTime = performance.now();
            
            // Update FPS counter
            this.updateFPS();
            
            // Check if enough time has passed since last scan
            const now = Date.now();
            if (now - this.lastScanTime < this.SCAN_INTERVAL) {
                requestAnimationFrame(processFrame);
                return;
            }
            
            try {
                // Check if video is ready
                if (this.video.readyState < 2) {
                    requestAnimationFrame(processFrame);
                    return;
                }
                
                // Draw the full video to canvas first
                this.context.drawImage(
                    this.video,
                    0, 0,
                    this.canvas.width, this.canvas.height
                );
                
                // Get image data from the scan region
                const imageData = this.context.getImageData(
                    this.scanRegion.x, this.scanRegion.y,
                    this.scanRegion.width, this.scanRegion.height
                );
                
                // Check if jsQR is available
                if (typeof jsQR === 'undefined') {
                    console.error('jsQR not available');
                    requestAnimationFrame(processFrame);
                    return;
                }
                
                // Agricultural QR Detection Strategy
                let code = null;
                
                // Strategy 1: Direct detection optimized for dense QR codes
                code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: 'dontInvert'
                });
                
                if (!code) {
                    // Strategy 2: Enhanced contrast for plastic packaging
                    this.enhanceImageForAgriculture(imageData);
                    code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: 'attemptBoth'
                    });
                }
                
                if (!code) {
                    // Strategy 3: Full frame scan for packet QR codes
                    const fullImageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
                    code = jsQR(fullImageData.data, fullImageData.width, fullImageData.height, {
                        inversionAttempts: 'attemptBoth'
                    });
                }
                
                if (code && code.data) {
                    console.log('🌾 Agricultural packet QR detected:', code.data);
                    
                    // Check for duplicate with shorter timeout for rapid scanning
                    if (code.data !== this.lastScanData || 
                        now - this.lastScanTime > this.DUPLICATE_TIMEOUT) {
                        
                        // Enhanced haptic for agricultural environment
                        if (navigator.vibrate) {
                            navigator.vibrate([100, 50, 100]);
                        }
                        
                        // Agricultural audio feedback
                        this.playAgriculturalBeep();
                        
                        // Process the QR code
                        this.handleQRCode(code.data);
                        this.lastScanData = code.data;
                        this.lastScanTime = now;
                        
                        // Visual feedback
                        this.flashSuccess();
                    }
                }
                
            } catch (error) {
                console.error('Scan error:', error);
            }
            
            // Monitor performance
            const processTime = performance.now() - startTime;
            if (processTime > this.MAX_PROCESS_TIME) {
                console.warn(`Frame processing took ${processTime.toFixed(1)}ms`);
            }
            
            // Continue scanning
            requestAnimationFrame(processFrame);
        };
        
        // Start the scanning loop
        requestAnimationFrame(processFrame);
    }
    
    handleQRCode(data) {
        this.updateStatus('QR code detected!', '#4CAF50');
        
        // Trigger the onScan callback if provided
        if (this.onScan) {
            this.onScan(data);
        }
        
        // Auto-reset status after short delay
        setTimeout(() => {
            if (this.scanActive) {
                this.updateStatus('Scanning...', '#4CAF50');
            }
        }, 1000);
    }
    
    flashSuccess() {
        const overlay = this.container.querySelector('.scanner-overlay');
        if (overlay) {
            overlay.style.animation = 'flash 0.3s';
            setTimeout(() => {
                overlay.style.animation = '';
            }, 300);
        }
        
        // Add flash animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes flash {
                0%, 100% { background: transparent; }
                50% { background: rgba(76, 175, 80, 0.3); }
            }
        `;
        if (!document.querySelector('style[data-flash]')) {
            style.setAttribute('data-flash', 'true');
            document.head.appendChild(style);
        }
    }
    
    updateStatus(message, color = '#4CAF50') {
        const statusDiv = document.getElementById('scan-status');
        if (statusDiv) {
            const statusText = statusDiv.querySelector('span:last-child');
            const statusDot = statusDiv.querySelector('.status-dot');
            if (statusText) statusText.textContent = message;
            if (statusDot) statusDot.style.background = color;
        }
    }
    
    updateFPS() {
        this.frameCount++;
        const now = Date.now();
        if (now - this.lastFpsUpdate >= 1000) {
            this.currentFps = this.frameCount;
            this.frameCount = 0;
            this.lastFpsUpdate = now;
            
            const fpsDiv = document.getElementById('fps-counter');
            if (fpsDiv) {
                fpsDiv.textContent = `${this.currentFps} FPS`;
            }
        }
    }
    
    async setupAgriculturalTorch() {
        if (!this.track) return;
        
        // Multiple attempts to enable torch for agricultural scanning
        let torchEnabled = false;
        
        try {
            // Method 1: Direct torch constraint
            if (this.track.getCapabilities) {
                const capabilities = this.track.getCapabilities();
                if (capabilities.torch) {
                    await this.track.applyConstraints({
                        advanced: [{ torch: true }]
                    });
                    torchEnabled = true;
                    console.log('🔦 Agricultural torch enabled via capabilities');
                }
            }
        } catch (e) {
            console.log('Method 1 failed:', e);
        }
        
        if (!torchEnabled) {
            try {
                // Method 2: Force torch setting
                await this.track.applyConstraints({
                    torch: true
                });
                torchEnabled = true;
                console.log('🔦 Agricultural torch enabled via direct constraint');
            } catch (e) {
                console.log('Method 2 failed:', e);
            }
        }
        
        if (!torchEnabled) {
            try {
                // Method 3: Settings object
                const settings = this.track.getSettings();
                if (settings && 'torch' in settings) {
                    await this.track.applyConstraints({
                        advanced: [{ torch: true }]
                    });
                    torchEnabled = true;
                    console.log('🔦 Agricultural torch enabled via settings');
                }
            } catch (e) {
                console.log('Method 3 failed:', e);
            }
        }
        
        // Update UI to show torch status
        this.torchEnabled = torchEnabled;
        const torchBtn = document.getElementById('torch-btn');
        if (torchBtn) {
            if (torchEnabled) {
                torchBtn.style.background = 'rgba(255, 235, 59, 0.8)';
                torchBtn.innerHTML = '<i class="fas fa-lightbulb" style="color: #FF8F00;"></i>';
                torchBtn.title = 'Agricultural Torch: ENABLED';
            } else {
                torchBtn.style.background = 'rgba(255, 255, 255, 0.2)';
                torchBtn.innerHTML = '<i class="fas fa-lightbulb"></i>';
                torchBtn.title = 'Torch not supported';
            }
        }
        
        if (torchEnabled) {
            console.log('🌾 Agricultural scanning optimized with auto-torch');
        } else {
            console.log('⚠️ Torch not available on this device');
        }
    }
    
    async optimizeCameraForAgriculture() {
        if (!this.track) return;
        
        try {
            // Enhanced constraints for agricultural QR packet scanning
            await this.track.applyConstraints({
                advanced: [
                    { focusMode: 'continuous' },
                    { exposureMode: 'continuous' },
                    { whiteBalanceMode: 'continuous' },
                    { zoom: 1.0 },
                    { brightness: 0.1 },
                    { contrast: 1.2 },
                    { saturation: 0.8 }
                ]
            });
            console.log('📹 Camera optimized for agricultural scanning');
        } catch (e) {
            // Try basic optimization if advanced fails
            try {
                await this.track.applyConstraints({
                    advanced: [
                        { focusMode: 'continuous' },
                        { exposureMode: 'continuous' }
                    ]
                });
            } catch (e2) {
                console.log('Camera optimization limited, using defaults');
            }
        }
    }

    enhanceImageForAgriculture(imageData) {
        const data = imageData.data;
        
        // Apply contrast enhancement for better QR detection on plastic packaging
        for (let i = 0; i < data.length; i += 4) {
            // Convert to grayscale with enhanced contrast
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            
            // Apply threshold for high contrast suitable for agricultural packets
            const enhanced = gray > 128 ? 255 : 0;
            
            data[i] = enhanced;     // Red
            data[i + 1] = enhanced; // Green
            data[i + 2] = enhanced; // Blue
            // Alpha channel remains unchanged
        }
    }
    
    playAgriculturalBeep() {
        try {
            // Create a more noticeable tone for agricultural environments
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Higher frequency for better outdoor audibility
            oscillator.frequency.setValueAtTime(1200, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime + 0.1);
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.2);
        } catch (e) {
            // Fallback for environments without Web Audio API
            console.log('Audio feedback not available');
        }
    }

    async toggleTorch() {
        if (!this.track || !this.track.getCapabilities) return;
        
        try {
            const capabilities = this.track.getCapabilities();
            if (capabilities.torch) {
                this.torchEnabled = !this.torchEnabled;
                await this.track.applyConstraints({
                    advanced: [{ torch: this.torchEnabled }]
                });
                
                const torchBtn = document.getElementById('torch-btn');
                if (torchBtn) {
                    torchBtn.style.background = this.torchEnabled ? 
                        'rgba(255, 235, 59, 0.3)' : 'rgba(255, 255, 255, 0.2)';
                    torchBtn.innerHTML = this.torchEnabled ?
                        '<i class="fas fa-lightbulb" style="color: #FFD700;"></i>' :
                        '<i class="fas fa-lightbulb"></i>';
                }
            }
        } catch (error) {
            console.error('Torch toggle error:', error);
        }
    }
    
    stop() {
        this.scanActive = false;
        
        if (this.video && this.video.srcObject) {
            const tracks = this.video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            this.video.srcObject = null;
        }
        
        this.updateStatus('Scanner stopped', '#9E9E9E');
    }
    
    restart() {
        this.stop();
        this.init();
    }
}

// Export for use in templates
window.InstantDetectionScanner = InstantDetectionScanner;