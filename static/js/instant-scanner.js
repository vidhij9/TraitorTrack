/**
 * Agricultural QR Scanner - Optimized for Supply Chain Packets
 * ============================================================
 * Ultra-fast detection of high-density QR codes on agricultural packaging
 * Features: Auto-torch, enhanced contrast, multi-region scanning
 */

class InstantScanner {
    constructor(containerId, onSuccess) {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.scanning = false;
        this.lastScan = '';
        this.lastScanTime = 0;
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.stream = null;
        this.frameCount = 0;
        this.torchEnabled = false; // Will be auto-enabled after torch setup
        this.torchSupported = false;
        
        // Ultra-fast settings optimized for agricultural packets
        this.scanEveryNFrames = 1; // Scan EVERY frame for instant detection
        this.duplicateTimeout = 200; // Even shorter for rapid scanning
        
        this.init();
    }
    
    init() {
        // Clear any existing content to prevent duplicates
        this.container.innerHTML = '';
        
        // Create fresh scanner UI
        this.container.innerHTML = `
            <div style="position:relative;width:100%;max-width:640px;margin:0 auto;">
                <video id="instant-video" autoplay playsinline muted 
                       style="width:100%;height:400px;object-fit:cover;border-radius:8px;background:#000;"></video>
                
                <canvas id="instant-canvas" style="display:none;"></canvas>
                
                <!-- Instant scan overlay -->
                <div style="position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;">
                    <div id="scan-frame" style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:280px;height:280px;border:2px solid #00ff00;border-radius:12px;transition:all 0.1s;">
                        <!-- Corner markers -->
                        <div style="position:absolute;top:-8px;left:-8px;width:40px;height:40px;border-left:4px solid #00ff00;border-top:4px solid #00ff00;border-radius:8px 0 0 0;"></div>
                        <div style="position:absolute;top:-8px;right:-8px;width:40px;height:40px;border-right:4px solid #00ff00;border-top:4px solid #00ff00;border-radius:0 8px 0 0;"></div>
                        <div style="position:absolute;bottom:-8px;left:-8px;width:40px;height:40px;border-left:4px solid #00ff00;border-bottom:4px solid #00ff00;border-radius:0 0 0 8px;"></div>
                        <div style="position:absolute;bottom:-8px;right:-8px;width:40px;height:40px;border-right:4px solid #00ff00;border-bottom:4px solid #00ff00;border-radius:0 0 8px 0;"></div>
                        
                        <!-- Scanning line animation -->
                        <div id="scan-line" style="position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg, transparent, #00ff00, transparent);animation:scan-line 2s infinite;"></div>
                    </div>
                </div>
                
                <!-- Status -->
                <div style="position:absolute;bottom:15px;left:0;right:0;text-align:center;">
                    <div id="instant-status" style="color:#00ff00;font-weight:bold;background:rgba(0,0,0,0.8);padding:10px 20px;border-radius:25px;display:inline-block;font-size:14px;">
                        ⚡ Initializing...
                    </div>
                    <div style="margin-top:10px;">
                        <button id="instant-torch" style="padding:12px 24px;background:#ff6b35;border:none;border-radius:25px;color:white;font-weight:bold;display:none;margin:0 5px;">
                            💡 Flash
                        </button>
                    </div>
                </div>
                
                <style>
                @keyframes scan-line {
                    0% { transform: translateY(0); opacity: 0; }
                    10% { opacity: 1; }
                    90% { opacity: 1; }
                    100% { transform: translateY(280px); opacity: 0; }
                }
                </style>
            </div>
        `;
        
        this.setupElements();
        this.startCamera();
    }
    
    setupElements() {
        this.video = document.getElementById('instant-video');
        this.canvas = document.getElementById('instant-canvas');
        this.ctx = this.canvas.getContext('2d', {
            willReadFrequently: true,
            alpha: false,
            desynchronized: true
        });
        this.status = document.getElementById('instant-status');
        this.torchBtn = document.getElementById('instant-torch');
        this.scanFrame = document.getElementById('scan-frame');
        
        // Torch control
        if (this.torchBtn) {
            this.torchBtn.addEventListener('click', () => this.toggleTorch());
        }
    }
    
    async startCamera() {
        try {
            this.updateStatus('⚡ Starting camera...', '#ffa500');
            
            // Ultra-optimized constraints for agricultural QR code packets
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1920, min: 1280 }, // Higher resolution for dense QR codes
                    height: { ideal: 1080, min: 720 },
                    frameRate: { ideal: 60, min: 30 }, // Maximum FPS for instant detection
                    focusMode: 'continuous',
                    exposureMode: 'continuous',
                    torch: true // Request torch to be on by default
                }
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints)
                .catch(() => navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } }))
                .catch(() => navigator.mediaDevices.getUserMedia({ video: true }));
            
            this.video.srcObject = this.stream;
            
            // Wait for video to be ready
            await new Promise((resolve) => {
                this.video.onloadedmetadata = () => {
                    this.video.play().then(resolve);
                };
            });
            
            // Setup torch if available
            await this.setupTorch();
            
            // Apply camera optimizations
            await this.optimizeCamera();
            
            this.updateStatus('⚡ Point at QR code', '#00ff00');
            this.startScanning();
            
        } catch (error) {
            console.error('Camera error:', error);
            this.updateStatus('❌ Camera error', '#ff0000');
        }
    }
    
    async setupTorch() {
        if (!this.stream) return;
        
        const track = this.stream.getVideoTracks()[0];
        if (!track) return;
        
        const capabilities = track.getCapabilities ? track.getCapabilities() : {};
        
        if (capabilities.torch) {
            this.torchBtn.style.display = 'inline-block';
            this.torchSupported = true;
            
            // Auto-enable torch by default for better QR code detection
            try {
                await track.applyConstraints({
                    advanced: [{ torch: true }]
                });
                this.torchEnabled = true;
                this.torchBtn.textContent = '💡 Flash ON';
                this.torchBtn.style.background = '#ff4444';
                console.log('🔦 Torch auto-enabled for optimal scanning');
            } catch (e) {
                console.log('Auto-torch enable failed, user can toggle manually');
            }
        }
    }
    
    async optimizeCamera() {
        if (!this.stream) return;
        
        const track = this.stream.getVideoTracks()[0];
        if (!track) return;
        
        try {
            // Enhanced constraints for agricultural QR packet scanning
            await track.applyConstraints({
                advanced: [
                    { focusMode: 'continuous' },
                    { exposureMode: 'continuous' },
                    { whiteBalanceMode: 'continuous' },
                    { zoom: 1.0 }, // No zoom for full detail
                    { brightness: 0.1 }, // Slight brightness boost for better contrast
                    { contrast: 1.2 }, // Enhanced contrast for QR readability
                    { saturation: 0.8 } // Reduced saturation for better B&W contrast
                ]
            });
            console.log('📹 Camera optimized for agricultural QR scanning');
        } catch (e) {
            // Try basic optimization if advanced fails
            try {
                await track.applyConstraints({
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
    
    async toggleTorch() {
        if (!this.torchSupported || !this.stream) return;
        
        const track = this.stream.getVideoTracks()[0];
        if (!track) return;
        
        this.torchEnabled = !this.torchEnabled;
        
        try {
            await track.applyConstraints({
                advanced: [{ torch: this.torchEnabled }]
            });
            
            this.torchBtn.textContent = this.torchEnabled ? '💡 Flash ON' : '💡 Flash';
            this.torchBtn.style.background = this.torchEnabled ? '#ff4444' : '#ff6b35';
        } catch (e) {
            console.log('Torch toggle failed');
        }
    }
    
    startScanning() {
        if (this.scanning) return;
        this.scanning = true;
        
        const scanLoop = () => {
            if (!this.scanning) return;
            
            // Check if video is ready
            if (this.video && this.video.readyState === 4) {
                // Instant scanning - scan EVERY frame
                if (this.frameCount % this.scanEveryNFrames === 0) {
                    this.instantDetection();
                }
                this.frameCount++;
            }
            
            requestAnimationFrame(scanLoop);
        };
        
        scanLoop();
    }
    
    instantDetection() {
        const videoWidth = this.video.videoWidth;
        const videoHeight = this.video.videoHeight;
        
        if (!videoWidth || !videoHeight) return;
        
        // Update canvas size if needed
        if (this.canvas.width !== videoWidth || this.canvas.height !== videoHeight) {
            this.canvas.width = videoWidth;
            this.canvas.height = videoHeight;
        }
        
        // Draw video frame with enhanced processing for agricultural packets
        this.ctx.clearRect(0, 0, videoWidth, videoHeight);
        this.ctx.drawImage(this.video, 0, 0);
        
        // STRATEGY 1: High-res full scan optimized for dense QR codes
        const imageData = this.ctx.getImageData(0, 0, videoWidth, videoHeight);
        let result = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'dontInvert'
        });
        
        if (result && result.data) {
            this.handleInstantSuccess(result.data);
            return;
        }
        
        // STRATEGY 2: Enhanced contrast for plastic packaging
        this.enhanceImageForQR(imageData);
        result = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'attemptBoth'
        });
        
        if (result && result.data) {
            this.handleInstantSuccess(result.data);
            return;
        }
        
        // STRATEGY 3: Multi-region scanning for packet labels
        const regions = this.getOptimalScanRegions(videoWidth, videoHeight);
        for (const region of regions) {
            const regionData = this.ctx.getImageData(region.x, region.y, region.width, region.height);
            result = jsQR(regionData.data, regionData.width, regionData.height, {
                inversionAttempts: 'attemptBoth'
            });
            
            if (result && result.data) {
                this.handleInstantSuccess(result.data);
                return;
            }
        }
    }
    
    enhanceImageForQR(imageData) {
        const data = imageData.data;
        
        // Apply contrast enhancement for better QR detection on plastic packaging
        for (let i = 0; i < data.length; i += 4) {
            // Convert to grayscale with enhanced contrast
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            
            // Apply threshold for high contrast
            const enhanced = gray > 128 ? 255 : 0;
            
            data[i] = enhanced;     // Red
            data[i + 1] = enhanced; // Green
            data[i + 2] = enhanced; // Blue
            // Alpha channel remains unchanged
        }
    }
    
    getOptimalScanRegions(width, height) {
        // Define regions optimized for agricultural packet QR placement
        return [
            // Bottom right (common QR location on packets)
            { x: width * 0.5, y: height * 0.6, width: width * 0.5, height: height * 0.4 },
            // Center area
            { x: width * 0.3, y: height * 0.3, width: width * 0.4, height: width * 0.4 },
            // Bottom left
            { x: 0, y: height * 0.6, width: width * 0.5, height: height * 0.4 },
            // Top right
            { x: width * 0.5, y: 0, width: width * 0.5, height: height * 0.4 }
        ];
    }
    
    handleInstantSuccess(qrData) {
        // Prevent duplicates with ultra-short timeout for agricultural workflow
        const now = Date.now();
        if (qrData === this.lastScan && (now - this.lastScanTime) < this.duplicateTimeout) {
            return;
        }
        
        this.lastScan = qrData;
        this.lastScanTime = now;
        
        console.log('🌾 Agricultural packet detected:', qrData);
        
        // INSTANT visual feedback
        this.flashSuccess();
        
        // Enhanced haptic for outdoor use
        if (navigator.vibrate) {
            navigator.vibrate([100, 50, 100]); // Double vibration for agricultural environment
        }
        
        // Instant beep with agricultural-friendly tone
        this.playAgriculturalBeep();
        
        // Immediate callback
        if (this.onSuccess) {
            this.onSuccess(qrData);
        }
        
        // Resume scanning very quickly for continuous workflow
        setTimeout(() => {
            this.updateStatus('⚡ Ready for next scan', '#00ff00');
        }, 200);
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
    
    flashSuccess() {
        // Instant visual feedback
        this.updateStatus('✅ Detected!', '#00ff00');
        
        // Flash the scan frame
        if (this.scanFrame) {
            this.scanFrame.style.borderColor = '#00ff00';
            this.scanFrame.style.boxShadow = '0 0 20px #00ff00';
            this.scanFrame.style.transform = 'translate(-50%, -50%) scale(1.1)';
            
            setTimeout(() => {
                this.scanFrame.style.borderColor = '#00ff00';
                this.scanFrame.style.boxShadow = 'none';
                this.scanFrame.style.transform = 'translate(-50%, -50%) scale(1)';
            }, 200);
        }
    }
    
    updateStatus(message, color = '#00ff00') {
        if (this.status) {
            this.status.textContent = message;
            this.status.style.color = color;
        }
    }
    
    stop() {
        this.scanning = false;
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        
        if (this.video) {
            this.video.srcObject = null;
        }
        
        // Clear the container to prevent duplicate UI elements
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

// Make available globally
window.InstantScanner = InstantScanner;