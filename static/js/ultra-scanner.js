/**
 * Ultra QR Scanner - Enhanced for Tiny QR Codes
 * =============================================
 * 
 * This scanner is specifically optimized for scanning tiny QR codes
 * with advanced focus control and image enhancement capabilities.
 */

class UltraQRScanner {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.options = {
            fps: 60,
            qrbox: { width: 300, height: 300 },
            aspectRatio: 1.0,
            supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA],
            ...options
        };
        
        this.html5QrCode = null;
        this.isScanning = false;
        this.stream = null;
        this.videoElement = null;
        this.canvasElement = null;
        
        // Enhanced detection settings
        this.detectionConfig = {
            minSize: 15, // Minimum QR code size in pixels
            maxZoom: 4.0, // Maximum digital zoom
            contrastBoost: 1.8,
            sharpnessBoost: 2.0,
            noiseReduction: true,
            adaptiveBrightness: true
        };
        
        this.setupElements();
    }
    
    setupElements() {
        // Create enhanced scanner container
        this.container.innerHTML = `
            <div class="ultra-scanner-wrapper">
                <div class="scanner-video-container">
                    <div id="${this.containerId}-reader" class="scanner-reader"></div>
                    <div class="scanner-overlay">
                        <div class="scan-target-area">
                            <div class="scan-corners">
                                <div class="corner corner-tl"></div>
                                <div class="corner corner-tr"></div>
                                <div class="corner corner-bl"></div>
                                <div class="corner corner-br"></div>
                            </div>
                            <div class="scan-line"></div>
                        </div>
                    </div>
                    <div class="scanner-controls">
                        <button id="focus-btn" class="control-btn">
                            <i class="fas fa-search-plus"></i>
                        </button>
                        <button id="torch-btn" class="control-btn">
                            <i class="fas fa-lightbulb"></i>
                        </button>
                        <button id="zoom-btn" class="control-btn">
                            <i class="fas fa-expand"></i>
                        </button>
                    </div>
                </div>
                <div class="scanner-stats">
                    <div class="stat-item">
                        <span class="stat-label">FPS:</span>
                        <span id="fps-counter">0</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Quality:</span>
                        <span id="quality-indicator">Good</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Focus:</span>
                        <span id="focus-indicator">Auto</span>
                    </div>
                </div>
            </div>
        `;
        
        this.addStyles();
        this.bindEvents();
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .ultra-scanner-wrapper {
                position: relative;
                width: 100%;
                max-width: 500px;
                margin: 0 auto;
                background: #000;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }
            
            .scanner-video-container {
                position: relative;
                width: 100%;
                aspect-ratio: 1;
                background: #000;
            }
            
            .scanner-reader {
                width: 100%;
                height: 100%;
            }
            
            .scanner-reader video {
                width: 100% !important;
                height: 100% !important;
                object-fit: cover;
                border-radius: 12px;
            }
            
            .scanner-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                pointer-events: none;
                z-index: 10;
            }
            
            .scan-target-area {
                position: relative;
                width: 280px;
                height: 280px;
                border: 2px solid rgba(0, 255, 0, 0.6);
                border-radius: 8px;
                background: rgba(0, 255, 0, 0.05);
                box-shadow: 
                    0 0 0 9999px rgba(0, 0, 0, 0.3),
                    inset 0 0 20px rgba(0, 255, 0, 0.2),
                    0 0 30px rgba(0, 255, 0, 0.4);
            }
            
            .scan-corners {
                position: absolute;
                top: -8px;
                left: -8px;
                right: -8px;
                bottom: -8px;
            }
            
            .corner {
                position: absolute;
                width: 32px;
                height: 32px;
                border: 4px solid #00ff00;
                border-radius: 4px;
            }
            
            .corner-tl {
                top: 0;
                left: 0;
                border-right: none;
                border-bottom: none;
                border-top-left-radius: 12px;
            }
            
            .corner-tr {
                top: 0;
                right: 0;
                border-left: none;
                border-bottom: none;
                border-top-right-radius: 12px;
            }
            
            .corner-bl {
                bottom: 0;
                left: 0;
                border-right: none;
                border-top: none;
                border-bottom-left-radius: 12px;
            }
            
            .corner-br {
                bottom: 0;
                right: 0;
                border-left: none;
                border-top: none;
                border-bottom-right-radius: 12px;
            }
            
            .scan-line {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: linear-gradient(90deg, transparent, #00ff00, transparent);
                border-radius: 2px;
                animation: scanline 2s ease-in-out infinite;
            }
            
            @keyframes scanline {
                0%, 100% { 
                    transform: translateY(0);
                    opacity: 1;
                }
                50% { 
                    transform: translateY(280px);
                    opacity: 0.8;
                }
            }
            
            .scanner-controls {
                position: absolute;
                bottom: 20px;
                right: 20px;
                display: flex;
                gap: 12px;
                pointer-events: all;
            }
            
            .control-btn {
                width: 48px;
                height: 48px;
                border: none;
                border-radius: 50%;
                background: rgba(0, 0, 0, 0.7);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
            }
            
            .control-btn:hover {
                background: rgba(0, 255, 0, 0.8);
                transform: scale(1.1);
            }
            
            .control-btn.active {
                background: #00ff00;
                color: #000;
            }
            
            .scanner-stats {
                padding: 12px 20px;
                background: rgba(0, 0, 0, 0.9);
                display: flex;
                justify-content: space-between;
                font-family: 'Courier New', monospace;
                font-size: 12px;
                color: #00ff00;
            }
            
            .stat-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 4px;
            }
            
            .stat-label {
                opacity: 0.7;
            }
            
            #fps-counter {
                font-weight: bold;
                font-size: 14px;
            }
            
            .quality-good { color: #00ff00; }
            .quality-fair { color: #ffaa00; }
            .quality-poor { color: #ff4444; }
            
            /* Success animation */
            .scan-success {
                animation: scanSuccess 0.5s ease-out;
            }
            
            @keyframes scanSuccess {
                0% { 
                    transform: scale(1);
                    box-shadow: 0 0 0 0 rgba(0, 255, 0, 0.8);
                }
                50% { 
                    transform: scale(1.05);
                    box-shadow: 0 0 0 20px rgba(0, 255, 0, 0);
                }
                100% { 
                    transform: scale(1);
                    box-shadow: 0 0 0 0 rgba(0, 255, 0, 0);
                }
            }
        `;
        
        document.head.appendChild(style);
    }
    
    bindEvents() {
        // Focus control
        const focusBtn = this.container.querySelector('#focus-btn');
        focusBtn.addEventListener('click', () => this.toggleFocus());
        
        // Torch control
        const torchBtn = this.container.querySelector('#torch-btn');
        torchBtn.addEventListener('click', () => this.toggleTorch());
        
        // Zoom control
        const zoomBtn = this.container.querySelector('#zoom-btn');
        zoomBtn.addEventListener('click', () => this.adjustZoom());
    }
    
    async start() {
        if (this.isScanning) return;
        
        try {
            // First ensure camera permissions
            await this.ensureCameraPermissions();
            
            this.html5QrCode = new Html5Qrcode(`${this.containerId}-reader`);
            
            // Get available cameras
            const cameras = await Html5Qrcode.getCameras();
            const rearCamera = cameras.find(camera => 
                camera.label.toLowerCase().includes('back') || 
                camera.label.toLowerCase().includes('rear') ||
                camera.label.toLowerCase().includes('environment')
            ) || cameras[0];
            
            if (!rearCamera) {
                throw new Error('No suitable camera found');
            }
            
            // Enhanced configuration for tiny QR codes
            const config = {
                fps: this.options.fps,
                qrbox: this.options.qrbox,
                aspectRatio: this.options.aspectRatio,
                supportedScanTypes: this.options.supportedScanTypes,
                
                // Advanced camera constraints
                videoConstraints: {
                    facingMode: 'environment',
                    width: { ideal: 3840, min: 1920 },
                    height: { ideal: 2160, min: 1080 },
                    frameRate: { ideal: 60, min: 30 },
                    focusMode: 'continuous',
                    exposureMode: 'continuous',
                    whiteBalanceMode: 'continuous'
                },
                
                // Enhanced detection
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true
                }
            };
            
            await this.html5QrCode.start(
                rearCamera.id,
                config,
                (decodedText, decodedResult) => this.onScanSuccess(decodedText, decodedResult),
                (errorMessage) => this.onScanError(errorMessage)
            );
            
            this.isScanning = true;
            
            // Start monitoring
            this.startMonitoring();
            
            // Apply advanced camera settings
            setTimeout(() => this.applyAdvancedSettings(), 1000);
            
            console.log('Ultra QR Scanner started successfully');
            
        } catch (error) {
            console.error('Failed to start Ultra QR Scanner:', error);
            throw error;
        }
    }
    
    async applyAdvancedSettings() {
        try {
            const videoElement = this.container.querySelector('video');
            if (!videoElement || !videoElement.srcObject) return;
            
            const stream = videoElement.srcObject;
            const videoTrack = stream.getVideoTracks()[0];
            
            if (!videoTrack) return;
            
            const capabilities = videoTrack.getCapabilities();
            const constraints = { advanced: [{}] };
            
            // Apply focus settings
            if (capabilities.focusMode && capabilities.focusMode.includes('continuous')) {
                constraints.advanced[0].focusMode = 'continuous';
            }
            
            // Apply exposure settings
            if (capabilities.exposureMode && capabilities.exposureMode.includes('continuous')) {
                constraints.advanced[0].exposureMode = 'continuous';
            }
            
            // Apply white balance
            if (capabilities.whiteBalanceMode && capabilities.whiteBalanceMode.includes('continuous')) {
                constraints.advanced[0].whiteBalanceMode = 'continuous';
            }
            
            // Apply zoom for better detail
            if (capabilities.zoom) {
                constraints.advanced[0].zoom = Math.min(2.0, capabilities.zoom.max);
            }
            
            await videoTrack.applyConstraints(constraints);
            
            console.log('Advanced camera settings applied');
            
        } catch (error) {
            console.warn('Could not apply advanced settings:', error);
        }
    }
    
    startMonitoring() {
        let frameCount = 0;
        let lastTime = performance.now();
        
        const updateStats = () => {
            if (!this.isScanning) return;
            
            frameCount++;
            const currentTime = performance.now();
            
            if (currentTime - lastTime >= 1000) {
                const fps = frameCount;
                frameCount = 0;
                lastTime = currentTime;
                
                // Update FPS counter
                const fpsCounter = this.container.querySelector('#fps-counter');
                if (fpsCounter) {
                    fpsCounter.textContent = fps;
                }
                
                // Update quality indicator
                this.updateQualityIndicator(fps);
            }
            
            requestAnimationFrame(updateStats);
        };
        
        updateStats();
    }
    
    updateQualityIndicator(fps) {
        const qualityIndicator = this.container.querySelector('#quality-indicator');
        if (!qualityIndicator) return;
        
        qualityIndicator.className = ''; // Reset classes
        
        if (fps >= 25) {
            qualityIndicator.textContent = 'Excellent';
            qualityIndicator.classList.add('quality-good');
        } else if (fps >= 15) {
            qualityIndicator.textContent = 'Good';
            qualityIndicator.classList.add('quality-good');
        } else if (fps >= 10) {
            qualityIndicator.textContent = 'Fair';
            qualityIndicator.classList.add('quality-fair');
        } else {
            qualityIndicator.textContent = 'Poor';
            qualityIndicator.classList.add('quality-poor');
        }
    }
    
    async toggleFocus() {
        const focusBtn = this.container.querySelector('#focus-btn');
        const focusIndicator = this.container.querySelector('#focus-indicator');
        
        try {
            const videoElement = this.container.querySelector('video');
            if (!videoElement || !videoElement.srcObject) return;
            
            const stream = videoElement.srcObject;
            const videoTrack = stream.getVideoTracks()[0];
            
            if (!videoTrack) return;
            
            const settings = videoTrack.getSettings();
            const capabilities = videoTrack.getCapabilities();
            
            if (capabilities.focusMode) {
                const currentMode = settings.focusMode || 'continuous';
                const newMode = currentMode === 'continuous' ? 'manual' : 'continuous';
                
                await videoTrack.applyConstraints({
                    advanced: [{ focusMode: newMode }]
                });
                
                focusIndicator.textContent = newMode === 'manual' ? 'Manual' : 'Auto';
                focusBtn.classList.toggle('active', newMode === 'manual');
            }
            
        } catch (error) {
            console.warn('Focus control failed:', error);
        }
    }
    
    async toggleTorch() {
        const torchBtn = this.container.querySelector('#torch-btn');
        
        try {
            const videoElement = this.container.querySelector('video');
            if (!videoElement || !videoElement.srcObject) return;
            
            const stream = videoElement.srcObject;
            const videoTrack = stream.getVideoTracks()[0];
            
            if (!videoTrack) return;
            
            const capabilities = videoTrack.getCapabilities();
            
            if (capabilities.torch) {
                const settings = videoTrack.getSettings();
                const torchOn = !settings.torch;
                
                await videoTrack.applyConstraints({
                    advanced: [{ torch: torchOn }]
                });
                
                torchBtn.classList.toggle('active', torchOn);
            }
            
        } catch (error) {
            console.warn('Torch control failed:', error);
        }
    }
    
    async adjustZoom() {
        const zoomBtn = this.container.querySelector('#zoom-btn');
        
        try {
            const videoElement = this.container.querySelector('video');
            if (!videoElement || !videoElement.srcObject) return;
            
            const stream = videoElement.srcObject;
            const videoTrack = stream.getVideoTracks()[0];
            
            if (!videoTrack) return;
            
            const capabilities = videoTrack.getCapabilities();
            
            if (capabilities.zoom) {
                const settings = videoTrack.getSettings();
                const currentZoom = settings.zoom || 1.0;
                const maxZoom = Math.min(capabilities.zoom.max, this.detectionConfig.maxZoom);
                
                // Cycle through zoom levels: 1x -> 2x -> 3x -> 1x
                let newZoom;
                if (currentZoom < 1.5) {
                    newZoom = 2.0;
                } else if (currentZoom < 2.5) {
                    newZoom = 3.0;
                } else {
                    newZoom = 1.0;
                }
                
                newZoom = Math.min(newZoom, maxZoom);
                
                await videoTrack.applyConstraints({
                    advanced: [{ zoom: newZoom }]
                });
                
                zoomBtn.classList.toggle('active', newZoom > 1.0);
                zoomBtn.innerHTML = `<i class="fas fa-expand"></i> ${newZoom.toFixed(1)}x`;
            }
            
        } catch (error) {
            console.warn('Zoom control failed:', error);
        }
    }
    
    onScanSuccess(decodedText, decodedResult) {
        console.log('QR Code scanned successfully:', decodedText);
        
        // Add success animation
        const targetArea = this.container.querySelector('.scan-target-area');
        targetArea.classList.add('scan-success');
        
        setTimeout(() => {
            targetArea.classList.remove('scan-success');
        }, 500);
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([100, 50, 100]);
        }
        
        // Call success callback
        if (this.onSuccess) {
            this.onSuccess(decodedText, decodedResult);
        }
        
        // Auto-stop after successful scan
        this.stop();
    }
    
    onScanError(errorMessage) {
        // Handle errors silently for better user experience
        // Only log significant errors
        if (!errorMessage.includes('No QR code found')) {
            console.log('Scan error:', errorMessage);
        }
    }
    
    async stop() {
        if (!this.isScanning) return;
        
        try {
            if (this.html5QrCode) {
                await this.html5QrCode.stop();
                this.html5QrCode = null;
            }
            
            this.isScanning = false;
            
            console.log('Ultra QR Scanner stopped');
            
        } catch (error) {
            console.error('Error stopping scanner:', error);
        }
    }
    
    async ensureCameraPermissions() {
        try {
            // For better browser compatibility, just try to access the camera directly
            // The browser will handle permission prompts automatically
            console.log('Checking camera access...');
            
            // Test camera access with minimal constraints
            const stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                } 
            });
            
            // Stop the test stream
            stream.getTracks().forEach(track => track.stop());
            
            console.log('Camera access confirmed');
            return true;
            
        } catch (error) {
            console.error('Camera access error:', error);
            
            let errorMessage = 'Camera access failed. ';
            if (error.name === 'NotAllowedError') {
                errorMessage += 'Please allow camera permissions in your browser.';
            } else if (error.name === 'NotFoundError') {
                errorMessage += 'No camera found on this device.';
            } else if (error.name === 'NotSupportedError') {
                errorMessage += 'Camera not supported by this browser.';
            } else {
                errorMessage += 'Please check camera permissions and try again.';
            }
            
            throw new Error(errorMessage);
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
}

// Export for global use
window.UltraQRScanner = UltraQRScanner;