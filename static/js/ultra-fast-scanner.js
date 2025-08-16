/**
 * Ultra Fast QR Scanner - Google Lens Speed
 * ==========================================
 * Optimized for maximum scanning speed
 */

class UltraFastScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.scanCanvas = null;
        this.scanContext = null;
        this.isScanning = false;
        this.onSuccess = null;
        this.cameraStream = null;
        this.lastScan = '';
        this.lastScanTime = 0;
        this.torchEnabled = false;
        this.scanWorker = null;
        
        // Performance optimizations
        this.targetWidth = 640;  // Lower resolution for faster processing
        this.targetHeight = 480;
        this.scanRegion = 0.6;   // Scan 60% center region
        this.continuousScan = true;
        this.frameCount = 0;
        
        console.log('UltraFast: Initializing');
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
            <div class="ultra-fast-scanner">
                <video id="${this.containerId}-video" autoplay playsinline muted></video>
                <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
                <canvas id="${this.containerId}-scan" style="display: none;"></canvas>
                
                <div class="scan-overlay">
                    <div class="scan-region">
                        <svg class="scan-frame" viewBox="0 0 200 200">
                            <path d="M20,0 L0,0 L0,20" stroke="#00ff00" stroke-width="3" fill="none"/>
                            <path d="M180,0 L200,0 L200,20" stroke="#00ff00" stroke-width="3" fill="none"/>
                            <path d="M20,200 L0,200 L0,180" stroke="#00ff00" stroke-width="3" fill="none"/>
                            <path d="M180,200 L200,200 L200,180" stroke="#00ff00" stroke-width="3" fill="none"/>
                            
                            <!-- Animated scan line -->
                            <line class="scan-line" x1="10" y1="0" x2="190" y2="0" 
                                  stroke="#00ff00" stroke-width="2" opacity="0.5">
                                <animateTransform
                                    attributeName="transform"
                                    type="translate"
                                    from="0 0"
                                    to="0 200"
                                    dur="2s"
                                    repeatCount="indefinite"/>
                            </line>
                        </svg>
                    </div>
                    <div class="scan-text">
                        <span class="status-text">Scanning...</span>
                        <span class="fps-counter"></span>
                    </div>
                </div>
                
                <div class="controls">
                    <button id="torch-btn" class="control-btn" title="Flashlight">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M6 14l3 3v5h6v-5l3-3V9H6v5zm5-12h2v3h-2V2zM3.5 5.875L4.914 4.46l2.12 2.122L5.62 7.997 3.5 5.875zm13.46.71l2.123-2.12 1.414 1.414L18.375 8l-2.122-2.122z"/>
                        </svg>
                    </button>
                </div>
                
                <div class="success-indicator" id="success-indicator"></div>
            </div>
            
            <style>
                .ultra-fast-scanner {
                    position: relative;
                    width: 100%;
                    max-width: 640px;
                    margin: 0 auto;
                    aspect-ratio: 4/3;
                    border-radius: 12px;
                    overflow: hidden;
                    background: #000;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                }
                
                #${this.containerId}-video {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    transform: scaleX(-1);
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
                
                .scan-region {
                    position: relative;
                    width: 200px;
                    height: 200px;
                    margin-bottom: 20px;
                }
                
                .scan-frame {
                    width: 100%;
                    height: 100%;
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.3; }
                }
                
                .scan-line {
                    animation: pulse 2s infinite;
                }
                
                .scan-text {
                    color: white;
                    font-size: 14px;
                    font-weight: 500;
                    text-shadow: 0 2px 4px rgba(0,0,0,0.8);
                    display: flex;
                    gap: 10px;
                    align-items: center;
                }
                
                .fps-counter {
                    font-size: 12px;
                    color: #00ff00;
                    font-family: monospace;
                }
                
                .controls {
                    position: absolute;
                    bottom: 20px;
                    right: 20px;
                    display: flex;
                    gap: 10px;
                }
                
                .control-btn {
                    width: 48px;
                    height: 48px;
                    border-radius: 50%;
                    background: rgba(255,255,255,0.15);
                    backdrop-filter: blur(10px);
                    border: 2px solid rgba(255,255,255,0.3);
                    color: white;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .control-btn:hover {
                    background: rgba(255,255,255,0.25);
                    transform: scale(1.05);
                }
                
                .control-btn.active {
                    background: #ffd700;
                    color: #000;
                    border-color: #ffd700;
                }
                
                .success-indicator {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: 100px;
                    height: 100px;
                    border-radius: 50%;
                    background: radial-gradient(circle, rgba(0,255,0,0.8) 0%, transparent 70%);
                    opacity: 0;
                    pointer-events: none;
                    transition: opacity 0.3s ease, transform 0.3s ease;
                }
                
                .success-indicator.show {
                    opacity: 1;
                    transform: translate(-50%, -50%) scale(2);
                }
                
                @media (max-width: 640px) {
                    .ultra-fast-scanner {
                        border-radius: 0;
                    }
                }
            </style>
        `;
    }
    
    setupElements() {
        this.video = document.getElementById(`${this.containerId}-video`);
        this.canvas = document.getElementById(`${this.containerId}-canvas`);
        this.context = this.canvas.getContext('2d', { 
            willReadFrequently: true,
            alpha: false,
            desynchronized: true
        });
        
        // Separate canvas for scanning (smaller size)
        this.scanCanvas = document.getElementById(`${this.containerId}-scan`);
        this.scanContext = this.scanCanvas.getContext('2d', {
            willReadFrequently: true,
            alpha: false,
            desynchronized: true
        });
        
        // Set scan canvas to optimized size
        this.scanCanvas.width = this.targetWidth;
        this.scanCanvas.height = this.targetHeight;
    }
    
    setupControls() {
        const torchBtn = document.getElementById('torch-btn');
        if (torchBtn) {
            torchBtn.addEventListener('click', () => this.toggleTorch());
        }
    }
    
    async startCamera() {
        try {
            // Optimized constraints for speed
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: this.targetWidth },
                    height: { ideal: this.targetHeight },
                    frameRate: { ideal: 60, min: 30 }, // Higher FPS for faster scanning
                    // Advanced settings for better performance
                    resizeMode: 'crop-and-scale',
                    aspectRatio: 4/3
                },
                audio: false
            };
            
            // Try to get camera with optimal settings
            this.cameraStream = await navigator.mediaDevices.getUserMedia(constraints)
                .catch(() => {
                    // Fallback to basic constraints
                    return navigator.mediaDevices.getUserMedia({ 
                        video: { facingMode: 'environment' }, 
                        audio: false 
                    });
                });
            
            this.video.srcObject = this.cameraStream;
            
            // Apply additional optimizations
            const track = this.cameraStream.getVideoTracks()[0];
            if (track && track.applyConstraints) {
                try {
                    await track.applyConstraints({
                        advanced: [
                            { focusMode: 'continuous' },
                            { exposureMode: 'continuous' },
                            { whiteBalanceMode: 'continuous' }
                        ]
                    });
                } catch (e) {
                    console.log('UltraFast: Advanced constraints not supported');
                }
            }
            
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play().then(resolve);
                };
            });
            
            // Check torch support
            this.checkTorchSupport();
            
            this.isScanning = true;
            this.startUltraFastScanning();
            this.updateStatus('Ready - Point at QR code');
            
        } catch (error) {
            console.error('UltraFast: Camera failed:', error);
            this.updateStatus('Camera error: ' + error.message);
        }
    }
    
    startUltraFastScanning() {
        if (typeof jsQR === 'undefined') {
            console.error('UltraFast: jsQR library not loaded');
            return;
        }
        
        let lastFrameTime = performance.now();
        let fpsFrames = [];
        
        const scan = () => {
            if (!this.isScanning) return;
            
            const currentTime = performance.now();
            const deltaTime = currentTime - lastFrameTime;
            lastFrameTime = currentTime;
            
            // Calculate FPS
            fpsFrames.push(1000 / deltaTime);
            if (fpsFrames.length > 30) {
                fpsFrames.shift();
                const avgFps = fpsFrames.reduce((a, b) => a + b) / fpsFrames.length;
                this.updateFPS(Math.round(avgFps));
            }
            
            if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
                // Draw to scan canvas at lower resolution
                this.scanContext.drawImage(
                    this.video, 
                    0, 0, 
                    this.targetWidth, 
                    this.targetHeight
                );
                
                // Get center region for faster processing
                const regionSize = Math.floor(this.targetWidth * this.scanRegion);
                const offsetX = Math.floor((this.targetWidth - regionSize) / 2);
                const offsetY = Math.floor((this.targetHeight - regionSize) / 2);
                
                const imageData = this.scanContext.getImageData(
                    offsetX, offsetY, 
                    regionSize, regionSize
                );
                
                // Ultra-fast scan with minimal processing
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: 'dontInvert' // Fastest option
                });
                
                if (code && code.data) {
                    this.handleSuccess(code.data);
                }
                
                this.frameCount++;
            }
            
            // Use requestAnimationFrame for smooth scanning
            requestAnimationFrame(scan);
        };
        
        // Start scanning immediately
        scan();
        console.log('UltraFast: Scanning started');
    }
    
    async checkTorchSupport() {
        const track = this.cameraStream?.getVideoTracks()[0];
        if (!track) return;
        
        try {
            const capabilities = track.getCapabilities ? track.getCapabilities() : {};
            if (capabilities.torch || capabilities.fillLightMode) {
                const torchBtn = document.getElementById('torch-btn');
                if (torchBtn) {
                    torchBtn.style.display = 'flex';
                }
            }
        } catch (e) {
            console.log('UltraFast: Torch check failed');
        }
    }
    
    async toggleTorch() {
        const track = this.cameraStream?.getVideoTracks()[0];
        if (!track) return;
        
        const torchBtn = document.getElementById('torch-btn');
        this.torchEnabled = !this.torchEnabled;
        
        try {
            await track.applyConstraints({
                advanced: [{ torch: this.torchEnabled }]
            });
            if (torchBtn) torchBtn.classList.toggle('active', this.torchEnabled);
        } catch (e) {
            console.log('UltraFast: Torch toggle failed');
        }
    }
    
    handleSuccess(qrText) {
        // Prevent duplicate scans
        const now = Date.now();
        if (qrText === this.lastScan && (now - this.lastScanTime) < 200) {
            return;
        }
        
        console.log('UltraFast: QR detected:', qrText);
        
        this.lastScan = qrText;
        this.lastScanTime = now;
        
        // Visual feedback
        this.showSuccessIndicator();
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(50);
        }
        
        // Audio feedback
        this.playSuccessSound();
        
        if (this.onSuccess) {
            this.onSuccess(qrText);
        }
        
        // Continue scanning if enabled
        if (!this.continuousScan) {
            this.isScanning = false;
            setTimeout(() => {
                this.isScanning = true;
            }, 1000);
        }
    }
    
    showSuccessIndicator() {
        const indicator = document.getElementById('success-indicator');
        if (indicator) {
            indicator.classList.add('show');
            setTimeout(() => indicator.classList.remove('show'), 300);
        }
    }
    
    playSuccessSound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800;
            oscillator.type = 'sine';
            gainNode.gain.value = 0.1;
            
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (e) {
            // Silent fail for audio
        }
    }
    
    updateStatus(message) {
        const statusText = this.container.querySelector('.status-text');
        if (statusText) {
            statusText.textContent = message;
        }
    }
    
    updateFPS(fps) {
        const fpsCounter = this.container.querySelector('.fps-counter');
        if (fpsCounter) {
            fpsCounter.textContent = `${fps} FPS`;
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
    
    async stop() {
        this.isScanning = false;
        
        if (this.cameraStream) {
            this.cameraStream.getTracks().forEach(track => track.stop());
            this.cameraStream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
        
        console.log('UltraFast: Stopped');
    }
}

// Make it available globally
window.UltraFastScanner = UltraFastScanner;