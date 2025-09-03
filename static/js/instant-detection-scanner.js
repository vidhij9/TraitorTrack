// Agricultural QR Scanner - Ultra-fast detection for agricultural supply chain packets
// Optimized for high-density QR codes on plastic packaging with auto-torch enabled

// Global scanner instance manager to prevent conflicts
window.activeScanners = window.activeScanners || new Map();

class InstantDetectionScanner {
    constructor(containerId, onSuccessCallback = null) {
        console.log('InstantDetectionScanner constructor called with:', {
            containerId,
            hasCallback: !!onSuccessCallback,
            callbackType: typeof onSuccessCallback
        });
        
        this.containerId = containerId;
        this.onSuccess = onSuccessCallback;
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
        this.stream = null; // Store stream reference for cleanup
        
        // Agricultural packet optimized settings - HIGH PERFORMANCE
        this.SCAN_INTERVAL = 16; // 60 FPS for fastest detection
        this.DUPLICATE_TIMEOUT = 200; // 200ms duplicate prevention (faster)
        this.VIDEO_WIDTH = 640; // Lower resolution for faster processing
        this.VIDEO_HEIGHT = 480;
        this.REGION_SIZE = 0.7; // 70% scan region for faster processing
        this.MAX_PROCESS_TIME = 20; // Tighter processing time limit
        
        // Performance monitoring
        this.frameCount = 0;
        this.lastFpsUpdate = Date.now();
        this.currentFps = 0;
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => this.stop());
        window.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pause();
            } else {
                this.resume();
            }
        });
        
        // Initialize immediately
        this.init();
    }
    
    async init() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            console.error('Container not found');
            return;
        }
        
        // Check for existing scanner instance
        if (window.activeScanners.has(this.containerId)) {
            console.log('Cleaning up existing scanner instance...');
            const existingScanner = window.activeScanners.get(this.containerId);
            await existingScanner.stop();
        }
        
        // Register this scanner instance
        window.activeScanners.set(this.containerId, this);
        
        // Clear any existing content
        this.container.innerHTML = '';
        
        // Create ultra-minimal UI
        this.createMinimalUI();
        
        // Start camera with delay to prevent conflicts
        setTimeout(() => {
            this.startCamera();
        }, 100);
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
        const maxRetries = 3;
        const retryDelay = [1000, 2000, 3000]; // Progressive delay
        
        for (let attempt = 0; attempt < maxRetries; attempt++) {
            try {
                this.updateStatus(`Initializing camera... (${attempt + 1}/${maxRetries})`, '#FFC107');
                console.log(`Camera access attempt ${attempt + 1}/${maxRetries}`);
                
                // Add timeout to prevent hanging
                const stream = await this.requestCameraWithTimeout();
                
                if (stream) {
                    return await this.setupCameraStream(stream);
                }
                
            } catch (error) {
                console.error(`Camera attempt ${attempt + 1} failed:`, error);
                
                if (attempt === maxRetries - 1) {
                    // Last attempt failed
                    this.handleCameraError(error);
                    return;
                }
                
                // Wait before retry
                this.updateStatus(`Camera busy, retrying in ${retryDelay[attempt]/1000}s...`, '#FF9800');
                await new Promise(resolve => setTimeout(resolve, retryDelay[attempt]));
            }
        }
    }
    
    async requestCameraWithTimeout(timeoutMs = 10000) {
        const constraints = {
            video: {
                facingMode: 'environment', // Force back camera, no fallback to front
                width: { ideal: this.VIDEO_WIDTH, max: 1280 },
                height: { ideal: this.VIDEO_HEIGHT, max: 720 },
                frameRate: { ideal: 60, min: 30 }, // Higher framerate for faster detection
                advanced: [{ torch: true }]
            }
        };
        
        // Create timeout promise
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => {
                reject(new Error('Camera initialization timeout - device may be in use'));
            }, timeoutMs);
        });
        
        // Race between camera request and timeout
        const cameraPromise = navigator.mediaDevices.getUserMedia(constraints);
        
        try {
            const stream = await Promise.race([cameraPromise, timeoutPromise]);
            console.log('✓ Camera stream obtained successfully');
            return stream;
        } catch (error) {
            // Try fallback with simpler constraints
            console.log('Primary camera request failed, trying fallback...');
            return await this.tryFallbackCamera();
        }
    }
    
    async tryFallbackCamera() {
        const fallbackConstraints = {
            video: {
                facingMode: 'environment', // Keep enforcing back camera
                width: { min: 320, ideal: 640 },
                height: { min: 240, ideal: 480 }
            }
        };
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia(fallbackConstraints);
            console.log('✓ Fallback camera stream obtained');
            return stream;
        } catch (error) {
            console.log('Fallback failed, trying basic constraints with back camera...');
            // Even in last resort, try to use back camera
            return await navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment' } 
            });
        }
    }
    
    async setupCameraStream(stream) {
        try {
            // Store stream reference for cleanup
            this.stream = stream;
            
            this.video.srcObject = stream;
            console.log('✓ Camera stream assigned to video element');
            
            // Store track for torch control
            this.track = stream.getVideoTracks()[0];
            
            // Setup torch with error handling
            try {
                await this.setupAgriculturalTorch();
            } catch (torchError) {
                console.warn('Torch setup failed (non-critical):', torchError);
            }
            
            // Apply camera optimizations with error handling
            try {
                await this.optimizeCameraForAgriculture();
            } catch (optimizeError) {
                console.warn('Camera optimization failed (non-critical):', optimizeError);
            }
            
            // Wait for video to be ready with timeout
            await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Video metadata load timeout'));
                }, 5000);
                
                this.video.onloadedmetadata = () => {
                    clearTimeout(timeout);
                    console.log('✓ Video ready, dimensions:', this.video.videoWidth, 'x', this.video.videoHeight);
                    this.video.play().then(() => {
                        resolve();
                    }).catch(reject);
                };
                
                // Handle case where metadata is already loaded
                if (this.video.readyState >= 1) {
                    clearTimeout(timeout);
                    this.video.play().then(() => {
                        resolve();
                    }).catch(reject);
                }
            });
            
            // Scan region is now initialized in initializeScanRegion method
            
            // Initialize scan region and start scanning
            this.initializeScanRegion();
            this.scanActive = true;
            this.updateStatus('Ready to scan', '#4CAF50');
            this.startScanning();
            
            console.log('✓ Camera initialization completed successfully');
            return true;
            
        } catch (error) {
            console.error('Camera setup error:', error);
            throw error;
        }
    }
    
    initializeScanRegion() {
        // Use actual video dimensions for region calculation with safety checks
        const actualWidth = (this.video && this.video.videoWidth) ? this.video.videoWidth : this.VIDEO_WIDTH;
        const actualHeight = (this.video && this.video.videoHeight) ? this.video.videoHeight : this.VIDEO_HEIGHT;
        
        // Calculate scan region (center 90% of frame)
        const regionOffset = (1 - this.REGION_SIZE) / 2;
        this.scanRegion = {
            x: Math.floor(actualWidth * regionOffset),
            y: Math.floor(actualHeight * regionOffset),
            width: Math.floor(actualWidth * this.REGION_SIZE),
            height: Math.floor(actualHeight * this.REGION_SIZE)
        };
        
        // Update canvas size to match scan region for better performance
        this.canvas.width = this.scanRegion.width;
        this.canvas.height = this.scanRegion.height;
        
        console.log('✓ Scan region initialized:', this.scanRegion);
    }
    
    handleCameraError(error) {
        console.error('Final camera error:', error);
        
        let errorMessage = 'Camera access failed';
        let suggestions = [];
        
        if (error.name === 'NotAllowedError' || error.message.includes('Permission denied')) {
            errorMessage = 'Camera permission denied';
            suggestions = [
                'Click the camera icon in your browser address bar',
                'Allow camera access and refresh the page'
            ];
        } else if (error.name === 'NotFoundError') {
            errorMessage = 'No camera found';
            suggestions = [
                'Check if your device has a camera',
                'Try using a different device'
            ];
        } else if (error.name === 'NotReadableError' || error.message.includes('in use')) {
            errorMessage = 'Camera is busy or in use';
            suggestions = [
                'Close other apps using the camera',
                'Refresh the page and try again',
                'Wait a moment and retry'
            ];
        } else if (error.message.includes('timeout')) {
            errorMessage = 'Camera initialization timed out';
            suggestions = [
                'Try refreshing the page',
                'Check if other apps are using the camera',
                'Wait a moment and try again'
            ];
        }
        
        // Show error with helpful suggestions
        this.updateStatus(errorMessage, '#F44336');
        
        // Add retry button
        const retryButton = document.createElement('button');
        retryButton.textContent = '🔄 Retry Camera';
        retryButton.style.cssText = `
            margin-top: 10px;
            padding: 10px 20px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        `;
        retryButton.onclick = () => {
            retryButton.remove();
            this.startCamera();
        };
        
        const statusDiv = document.getElementById('scan-status');
        if (statusDiv) {
            statusDiv.appendChild(retryButton);
        }
        
        // Show suggestions
        if (suggestions.length > 0) {
            const suggestionDiv = document.createElement('div');
            suggestionDiv.style.cssText = `
                margin-top: 10px;
                padding: 10px;
                background: rgba(255, 235, 59, 0.1);
                border: 1px solid #FFC107;
                border-radius: 5px;
                font-size: 12px;
                line-height: 1.4;
            `;
            suggestionDiv.innerHTML = '<strong>Try this:</strong><ul>' + 
                suggestions.map(s => `<li>${s}</li>`).join('') + '</ul>';
            
            const container = this.container.querySelector('.instant-scanner-container');
            if (container) {
                container.appendChild(suggestionDiv);
            }
        }
    }
    
    startScanning() {
        if (!this.scanActive) return;
        
        const processFrame = () => {
            if (!this.scanActive) return;
            
            const startTime = performance.now();
            
            // Update FPS counter less frequently
            if (this.frameCount % 10 === 0) {
                this.updateFPS();
            }
            
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
                
                // Draw only the scan region to canvas for better performance
                this.context.drawImage(
                    this.video,
                    this.scanRegion.x, this.scanRegion.y,
                    this.scanRegion.width, this.scanRegion.height,
                    0, 0,
                    this.scanRegion.width, this.scanRegion.height
                );
                
                // Get image data from the drawn region
                const imageData = this.context.getImageData(
                    0, 0,
                    this.scanRegion.width, this.scanRegion.height
                );
                
                // Check if jsQR is available
                if (typeof jsQR === 'undefined') {
                    console.error('jsQR not available');
                    requestAnimationFrame(processFrame);
                    return;
                }
                
                // Ultra-fast QR detection - single attempt only for speed
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: 'dontInvert' // Single pass for maximum speed
                });
                
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
    
    // Resource management methods
    stop() {
        console.log('Stopping scanner and cleaning up resources...');
        
        this.scanActive = false;
        
        // Stop video stream
        if (this.stream) {
            this.stream.getTracks().forEach(track => {
                console.log('Stopping track:', track.kind);
                track.stop();
            });
            this.stream = null;
        }
        
        // Clear video source
        if (this.video) {
            this.video.srcObject = null;
        }
        
        // Remove from active scanners
        if (window.activeScanners && window.activeScanners.has(this.containerId)) {
            window.activeScanners.delete(this.containerId);
        }
        
        console.log('✓ Scanner cleanup completed');
    }
    
    pause() {
        console.log('Pausing scanner...');
        this.scanActive = false;
        this.updateStatus('Paused', '#FFC107');
    }
    
    resume() {
        console.log('Resuming scanner...');
        if (this.video && this.video.srcObject) {
            this.scanActive = true;
            this.updateStatus('Scanning...', '#4CAF50');
            this.startScanning();
        } else {
            // Restart camera if stream was lost
            this.startCamera();
        }
    }
    
    // New methods for pausing/resuming scanning without stopping camera
    pauseScanning() {
        console.log('Pausing scanning (camera stays on)...');
        this.scanActive = false;
        this.updateStatus('Processing...', '#FFC107');
    }
    
    resumeScanning() {
        console.log('Resuming scanning...');
        if (this.video && this.video.srcObject && !this.scanActive) {
            this.scanActive = true;
            this.updateStatus('Ready to scan', '#4CAF50');
            this.startScanning();
        }
    }
    
    // Improved cleanup on page hide/show
    handleVisibilityChange() {
        if (document.hidden) {
            this.pause();
        } else {
            setTimeout(() => this.resume(), 500); // Small delay to ensure page is ready
        }
    }
    
    handleQRCode(data) {
        console.log('handleQRCode called with data:', {
            data: data,
            dataLength: data ? data.length : 0,
            hasCallback: !!this.onSuccess,
            callbackType: typeof this.onSuccess
        });
        
        // IMMEDIATELY PAUSE SCANNER after QR detection
        this.pauseScanning();
        this.updateStatus('QR detected, paused', '#FFC107');
        
        // Trigger the success callback if provided
        // Support both onSuccess and onScan for compatibility
        const callback = this.onScan || this.onSuccess;
        
        if (callback && typeof callback === 'function') {
            console.log('Calling scan callback with data:', data);
            try {
                // The callback should handle resuming the scanner when ready
                callback(data);
            } catch (error) {
                console.error('Error calling scan callback:', error);
                // Resume scanning after error
                setTimeout(() => this.resumeScanning(), 2000);
            }
        } else {
            console.warn('No scan callback provided (checked onScan and onSuccess)');
            // Resume scanning if no callback
            setTimeout(() => this.resumeScanning(), 2000);
        }
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
            // Simplified camera optimization for better FPS
            await this.track.applyConstraints({
                advanced: [
                    { focusMode: 'continuous' }
                ]
            });
            console.log('📹 Camera optimized for agricultural scanning');
        } catch (e) {
            console.log('Camera optimization not supported, using defaults');
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
    
    start() {
        if (!this.scanActive) {
            this.startCamera();
        }
    }
    
    restart() {
        this.stop();
        this.init();
    }
}

// Export for use in templates
window.InstantDetectionScanner = InstantDetectionScanner;