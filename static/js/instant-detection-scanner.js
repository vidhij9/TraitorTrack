// Instant Detection Scanner - Ultra-aggressive optimization for sub-second QR detection
// Designed to achieve Google Lens-like performance with instant detection

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
        this.track = null;
        
        // Ultra-aggressive performance settings
        this.SCAN_INTERVAL = 16; // 60 FPS scanning
        this.DUPLICATE_TIMEOUT = 200; // 200ms duplicate prevention (very short)
        this.VIDEO_WIDTH = 640; // Optimal resolution for speed
        this.VIDEO_HEIGHT = 480;
        this.REGION_SIZE = 0.6; // Scan 60% center region for faster processing
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
            height: auto;
            display: block;
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
        
        // Create torch button
        const torchBtn = document.createElement('button');
        torchBtn.id = 'torch-btn';
        torchBtn.className = 'btn btn-secondary';
        torchBtn.style.cssText = `
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid #fff;
            color: #fff;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 10;
        `;
        torchBtn.innerHTML = '<i class="fas fa-lightbulb"></i>';
        torchBtn.onclick = () => this.toggleTorch();
        
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
            
            // Request camera with optimized constraints
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: this.VIDEO_WIDTH },
                    height: { ideal: this.VIDEO_HEIGHT },
                    frameRate: { ideal: 60, min: 30 }, // High frame rate
                    focusMode: { ideal: 'continuous' },
                    exposureMode: { ideal: 'continuous' },
                    whiteBalanceMode: { ideal: 'continuous' }
                }
            };
            
            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = stream;
            
            // Store track for torch control
            this.track = stream.getVideoTracks()[0];
            
            // Check torch capability
            if (this.track && this.track.getCapabilities) {
                const capabilities = this.track.getCapabilities();
                if (capabilities.torch) {
                    document.getElementById('torch-btn').style.display = 'flex';
                } else {
                    document.getElementById('torch-btn').style.display = 'none';
                }
            }
            
            // Wait for video to be ready
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play();
                    resolve();
                };
            });
            
            // Calculate scan region (center 60% of frame)
            const regionOffset = (1 - this.REGION_SIZE) / 2;
            this.scanRegion = {
                x: Math.floor(this.VIDEO_WIDTH * regionOffset),
                y: Math.floor(this.VIDEO_HEIGHT * regionOffset),
                width: Math.floor(this.VIDEO_WIDTH * this.REGION_SIZE),
                height: Math.floor(this.VIDEO_HEIGHT * this.REGION_SIZE)
            };
            
            // Start scanning immediately
            this.scanActive = true;
            this.updateStatus('Scanning...', '#4CAF50');
            this.startScanning();
            
        } catch (error) {
            console.error('Camera error:', error);
            this.updateStatus('Camera access denied', '#F44336');
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
                // Draw only the scan region to canvas for faster processing
                this.context.drawImage(
                    this.video,
                    this.scanRegion.x, this.scanRegion.y,
                    this.scanRegion.width, this.scanRegion.height,
                    0, 0,
                    this.scanRegion.width, this.scanRegion.height
                );
                
                // Get image data from the scan region
                const imageData = this.context.getImageData(
                    0, 0,
                    this.scanRegion.width,
                    this.scanRegion.height
                );
                
                // Try to detect QR code with ultra-fast jsQR
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: 'attemptBoth' // Try both normal and inverted
                });
                
                if (code && code.data) {
                    // Check for duplicate
                    if (code.data !== this.lastScanData || 
                        now - this.lastScanTime > this.DUPLICATE_TIMEOUT) {
                        
                        // Haptic feedback if available
                        if (navigator.vibrate) {
                            navigator.vibrate(50);
                        }
                        
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