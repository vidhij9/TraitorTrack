/**
 * Google Lens-Like QR Scanner for Agricultural Seed Bags
 * Optimized for instant detection like Google Lens
 */
class GoogleLensScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.scanner = null;
        this.isScanning = false;
        this.lastScanTime = 0;
        this.scanCooldown = 100; // Ultra-fast scanning like Google Lens
        this.detectionCount = 0;
        this.consecutiveDetections = 0;
        this.requiredDetections = 2; // Confirm detection like Google Lens
        
        // Google Lens-like constraints
        this.optimalConstraints = {
            video: {
                facingMode: { ideal: 'environment' },
                width: { ideal: 1920, min: 1280 },
                height: { ideal: 1080, min: 720 },
                frameRate: { ideal: 60, min: 30 },
                focusMode: { ideal: 'continuous' },
                exposureMode: { ideal: 'continuous' },
                whiteBalanceMode: { ideal: 'continuous' },
                zoom: { ideal: 1.0 }
            },
            audio: false
        };
        
        this.init();
    }
    
    init() {
        this.createUI();
        this.setupEventHandlers();
    }
    
    createUI() {
        this.container.innerHTML = `
            <div class="google-lens-scanner">
                <div id="qr-reader-${this.containerId}" class="scanner-viewport"></div>
                <div class="scanner-overlay">
                    <div class="scan-frame">
                        <div class="corner-frame top-left"></div>
                        <div class="corner-frame top-right"></div>
                        <div class="corner-frame bottom-left"></div>
                        <div class="corner-frame bottom-right"></div>
                    </div>
                    <div class="scan-instructions">
                        <div class="scan-status" id="scan-status-${this.containerId}">
                            <i class="fas fa-qrcode"></i> Point camera at QR code
                        </div>
                        <div class="scan-tips">
                            Hold steady • Ensure good lighting • Clean lens if needed
                        </div>
                    </div>
                </div>
                <div class="scanner-controls">
                    <button class="control-btn" id="torch-btn-${this.containerId}">
                        <i class="fas fa-flashlight"></i>
                    </button>
                    <button class="control-btn" id="flip-btn-${this.containerId}">
                        <i class="fas fa-camera-rotate"></i>
                    </button>
                </div>
            </div>
            
            <style>
            .google-lens-scanner {
                position: relative;
                width: 100%;
                height: 400px;
                background: #000;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            }
            
            .scanner-viewport {
                width: 100%;
                height: 100%;
                position: relative;
            }
            
            .scanner-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                pointer-events: none;
                z-index: 10;
            }
            
            .scan-frame {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 250px;
                height: 250px;
                border: 2px solid rgba(255,255,255,0.3);
                border-radius: 12px;
            }
            
            .corner-frame {
                position: absolute;
                width: 30px;
                height: 30px;
                border: 3px solid #00ff88;
                border-radius: 4px;
            }
            
            .corner-frame.top-left {
                top: -3px;
                left: -3px;
                border-right: none;
                border-bottom: none;
            }
            
            .corner-frame.top-right {
                top: -3px;
                right: -3px;
                border-left: none;
                border-bottom: none;
            }
            
            .corner-frame.bottom-left {
                bottom: -3px;
                left: -3px;
                border-right: none;
                border-top: none;
            }
            
            .corner-frame.bottom-right {
                bottom: -3px;
                right: -3px;
                border-left: none;
                border-top: none;
            }
            
            .scan-instructions {
                position: absolute;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                text-align: center;
                color: white;
            }
            
            .scan-status {
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }
            
            .scan-tips {
                font-size: 12px;
                opacity: 0.8;
                background: rgba(0,0,0,0.5);
                padding: 4px 12px;
                border-radius: 20px;
            }
            
            .scanner-controls {
                position: absolute;
                bottom: 15px;
                right: 15px;
                display: flex;
                gap: 10px;
                z-index: 15;
            }
            
            .control-btn {
                width: 44px;
                height: 44px;
                border: none;
                border-radius: 22px;
                background: rgba(255,255,255,0.9);
                color: #333;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.3s;
                backdrop-filter: blur(10px);
            }
            
            .control-btn:hover {
                background: white;
                transform: scale(1.1);
            }
            
            .control-btn.active {
                background: #00ff88;
                color: white;
            }
            
            @keyframes scan-pulse {
                0% { box-shadow: 0 0 0 0 rgba(0,255,136,0.4); }
                70% { box-shadow: 0 0 0 20px rgba(0,255,136,0); }
                100% { box-shadow: 0 0 0 0 rgba(0,255,136,0); }
            }
            
            .scanning .scan-frame {
                animation: scan-pulse 2s infinite;
            }
            
            .detected .corner-frame {
                border-color: #ff6b00;
                animation: detected-pulse 0.5s ease-out;
            }
            
            @keyframes detected-pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); }
                100% { transform: scale(1); }
            }
            </style>
        `;
    }
    
    setupEventHandlers() {
        // Torch control
        const torchBtn = document.getElementById(`torch-btn-${this.containerId}`);
        if (torchBtn) {
            torchBtn.addEventListener('click', () => this.toggleTorch());
        }
        
        // Camera flip control
        const flipBtn = document.getElementById(`flip-btn-${this.containerId}`);
        if (flipBtn) {
            flipBtn.addEventListener('click', () => this.flipCamera());
        }
    }
    
    async start() {
        if (this.isScanning) return;
        
        try {
            this.updateStatus('<i class="fas fa-spinner fa-spin"></i> Initializing camera...', 'info');
            
            // Use enhanced camera manager if available
            if (window.cameraFixManager) {
                await window.cameraFixManager.testCameraAccess();
            }
            
            const readerId = `qr-reader-${this.containerId}`;
            this.scanner = new Html5Qrcode(readerId);
            
            // Get available cameras
            const cameras = await Html5Qrcode.getCameras();
            if (!cameras || cameras.length === 0) {
                throw new Error('No cameras found');
            }
            
            // Select back camera preferentially
            const backCamera = cameras.find(camera => 
                camera.label.toLowerCase().includes('back') ||
                camera.label.toLowerCase().includes('rear') ||
                camera.label.toLowerCase().includes('environment')
            ) || cameras[cameras.length - 1];
            
            console.log(`🎯 Using camera: ${backCamera.label}`);
            
            // Google Lens-like configuration
            const config = {
                fps: 60, // High frame rate like Google Lens
                qrbox: function(viewfinderWidth, viewfinderHeight) {
                    // Dynamic QR box like Google Lens
                    const minEdgePercentage = 0.7;
                    const minEdgeSize = Math.min(viewfinderWidth, viewfinderHeight);
                    const qrboxSize = Math.floor(minEdgeSize * minEdgePercentage);
                    return {
                        width: qrboxSize,
                        height: qrboxSize
                    };
                },
                aspectRatio: 1.77778, // 16:9 like Google Lens
                disableFlip: false,
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true // Use native detection when available
                },
                formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
                rememberLastUsedCamera: true
            };
            
            await this.scanner.start(
                backCamera.id,
                config,
                (decodedText, decodedResult) => this.onScanSuccess(decodedText, decodedResult),
                (error) => this.onScanError(error)
            );
            
            this.isScanning = true;
            this.updateStatus('<i class="fas fa-qrcode"></i> Ready to scan', 'ready');
            this.container.querySelector('.google-lens-scanner').classList.add('scanning');
            
            // Auto-enable torch for agricultural scanning
            setTimeout(() => this.enableTorch(), 1000);
            
            console.log('Google Lens-like scanner started successfully');
            
        } catch (error) {
            console.error('Failed to start scanner:', error);
            this.handleScannerError(error);
        }
    }
    
    onScanSuccess(decodedText, decodedResult) {
        const now = Date.now();
        
        // Prevent duplicate scans (like Google Lens)
        if (decodedText === this.lastResult && (now - this.lastScanTime) < this.scanCooldown) {
            return;
        }
        
        // Consecutive detection confirmation (Google Lens-like behavior)
        if (decodedText === this.lastResult) {
            this.consecutiveDetections++;
        } else {
            this.consecutiveDetections = 1;
            this.lastResult = decodedText;
        }
        
        // Require multiple detections for stability
        if (this.consecutiveDetections >= this.requiredDetections) {
            this.lastScanTime = now;
            this.detectionCount++;
            
            // Visual feedback like Google Lens
            this.showDetectedAnimation();
            
            // Haptic feedback
            if (navigator.vibrate) {
                navigator.vibrate([100, 50, 100]); // Google Lens-like pattern
            }
            
            // Audio feedback
            this.playDetectionSound();
            
            // Update status
            this.updateStatus(`<i class="fas fa-check-circle"></i> Detected: ${decodedText}`, 'success');
            
            console.log(`🌾 Agricultural QR detected (attempt ${this.detectionCount}):`, decodedText);
            
            // Call success handler
            if (this.onSuccess) {
                this.onSuccess(decodedText, decodedResult);
            }
            
            // Reset for next scan
            this.consecutiveDetections = 0;
        }
    }
    
    onScanError(error) {
        // Ignore common scanning errors (Google Lens approach)
        if (error.includes('No MultiFormat Readers') || 
            error.includes('NotFoundException') ||
            error.includes('No QR code found')) {
            return; // Silent ignore like Google Lens
        }
        
        // Only log significant errors
        if (this.detectionCount === 0) {
            console.warn('Scanner error:', error);
        }
    }
    
    showDetectedAnimation() {
        const scanner = this.container.querySelector('.google-lens-scanner');
        scanner.classList.add('detected');
        setTimeout(() => {
            scanner.classList.remove('detected');
        }, 500);
    }
    
    playDetectionSound() {
        try {
            // Create a subtle beep like Google Lens
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(1000, audioContext.currentTime);
            oscillator.frequency.exponentialRampToValueAtTime(800, audioContext.currentTime + 0.1);
            
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (e) {
            console.log('Audio not available');
        }
    }
    
    async enableTorch() {
        try {
            if (this.scanner && this.scanner.getRunningTrackCameraCapabilities) {
                const capabilities = this.scanner.getRunningTrackCameraCapabilities();
                if (capabilities && capabilities.torch) {
                    await this.scanner.applyVideoConstraints({
                        advanced: [{ torch: true }]
                    });
                    
                    const torchBtn = document.getElementById(`torch-btn-${this.containerId}`);
                    if (torchBtn) {
                        torchBtn.classList.add('active');
                    }
                    
                    console.log('🔦 Torch enabled for agricultural scanning');
                }
            }
        } catch (error) {
            console.log('Torch not available:', error.message);
        }
    }
    
    async toggleTorch() {
        try {
            const torchBtn = document.getElementById(`torch-btn-${this.containerId}`);
            const isActive = torchBtn.classList.contains('active');
            
            if (this.scanner && this.scanner.applyVideoConstraints) {
                await this.scanner.applyVideoConstraints({
                    advanced: [{ torch: !isActive }]
                });
                
                torchBtn.classList.toggle('active');
                console.log(`🔦 Torch ${!isActive ? 'enabled' : 'disabled'}`);
            }
        } catch (error) {
            console.log('Cannot toggle torch:', error.message);
        }
    }
    
    async flipCamera() {
        // TODO: Implement camera flip functionality
        console.log('Camera flip requested');
    }
    
    updateStatus(message, type = 'info') {
        const statusEl = document.getElementById(`scan-status-${this.containerId}`);
        if (statusEl) {
            statusEl.innerHTML = message;
            statusEl.className = `scan-status status-${type}`;
        }
    }
    
    handleScannerError(error) {
        let message = 'Camera error';
        let suggestions = [];
        
        switch (error.name || error.message) {
            case 'NotAllowedError':
                message = '📱 Camera permission denied';
                suggestions = [
                    'Click the camera icon in your browser address bar',
                    'Allow camera access for this website',
                    'Refresh the page and try again'
                ];
                break;
            case 'NotFoundError':
                message = '📷 No camera found';
                suggestions = [
                    'Make sure your device has a camera',
                    'Try using a different browser'
                ];
                break;
            case 'NotReadableError':
                message = '⚡ Camera is busy';
                suggestions = [
                    'Close other apps using the camera',
                    'Restart your browser'
                ];
                break;
            default:
                message = `⚠️ ${error.message || 'Scanner error'}`;
                suggestions = [
                    'Try refreshing the page',
                    'Use Chrome or Safari browser',
                    'Ensure HTTPS connection'
                ];
        }
        
        this.updateStatus(message, 'error');
        
        // Show detailed error help
        const helpHtml = `
            <div class="scanner-error-help">
                <h6>${message}</h6>
                <ul>
                    ${suggestions.map(s => `<li>${s}</li>`).join('')}
                </ul>
                <button class="btn btn-primary btn-sm" onclick="location.reload()">
                    <i class="fas fa-refresh"></i> Try Again
                </button>
            </div>
        `;
        
        this.container.innerHTML += helpHtml;
    }
    
    async stop() {
        if (this.scanner && this.isScanning) {
            try {
                await this.scanner.stop();
                this.isScanning = false;
                console.log('Scanner stopped');
            } catch (error) {
                console.error('Error stopping scanner:', error);
            }
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
}

// Global export
window.GoogleLensScanner = GoogleLensScanner;