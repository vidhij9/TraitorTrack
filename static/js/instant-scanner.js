/**
 * Instant QR Scanner - Google Lens Speed
 * =======================================
 * Ultra-optimized for instant detection with zero delay
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
        this.torchEnabled = false;
        
        // Ultra-fast settings
        this.scanEveryNFrames = 1; // Scan EVERY frame for instant detection
        this.duplicateTimeout = 300; // Shorter duplicate prevention
        
        this.init();
    }
    
    init() {
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
            
            // Ultra-optimized constraints for instant scanning
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280, min: 640 },
                    height: { ideal: 720, min: 480 },
                    frameRate: { ideal: 60, min: 30 }, // Maximum FPS for instant detection
                    focusMode: 'continuous',
                    exposureMode: 'continuous'
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
        }
    }
    
    async optimizeCamera() {
        if (!this.stream) return;
        
        const track = this.stream.getVideoTracks()[0];
        if (!track) return;
        
        try {
            await track.applyConstraints({
                advanced: [
                    { focusMode: 'continuous' },
                    { exposureMode: 'continuous' },
                    { whiteBalanceMode: 'continuous' }
                ]
            });
        } catch (e) {
            // Silent fail - camera might not support these
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
        
        // Draw video frame
        this.ctx.drawImage(this.video, 0, 0);
        
        // INSTANT STRATEGY 1: Direct full scan (fastest, works 90% of time)
        const imageData = this.ctx.getImageData(0, 0, videoWidth, videoHeight);
        let result = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'dontInvert' // Faster with no inversion
        });
        
        if (result && result.data) {
            this.handleInstantSuccess(result.data);
            return;
        }
        
        // INSTANT STRATEGY 2: Try with inversion (for inverted QR codes)
        result = jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: 'invertFirst'
        });
        
        if (result && result.data) {
            this.handleInstantSuccess(result.data);
            return;
        }
        
        // INSTANT STRATEGY 3: Center crop only if first two fail (minimal overhead)
        const size = Math.min(videoWidth, videoHeight) * 0.7;
        const x = (videoWidth - size) / 2;
        const y = (videoHeight - size) / 2;
        
        const centerData = this.ctx.getImageData(x, y, size, size);
        result = jsQR(centerData.data, centerData.width, centerData.height, {
            inversionAttempts: 'attemptBoth'
        });
        
        if (result && result.data) {
            this.handleInstantSuccess(result.data);
        }
    }
    
    handleInstantSuccess(qrData) {
        // Prevent duplicates with shorter timeout for faster rescanning
        const now = Date.now();
        if (qrData === this.lastScan && (now - this.lastScanTime) < this.duplicateTimeout) {
            return;
        }
        
        this.lastScan = qrData;
        this.lastScanTime = now;
        
        console.log('⚡ Instant detection:', qrData);
        
        // INSTANT visual feedback
        this.flashSuccess();
        
        // Quick haptic
        if (navigator.vibrate) {
            navigator.vibrate(50); // Single short vibration
        }
        
        // Instant beep
        this.playInstantBeep();
        
        // Immediate callback
        if (this.onSuccess) {
            this.onSuccess(qrData);
        }
        
        // Resume scanning almost immediately
        setTimeout(() => {
            this.updateStatus('⚡ Scanning...', '#00ff00');
        }, 300);
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
    
    playInstantBeep() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 1500; // Higher pitch for instant feedback
            oscillator.type = 'sine';
            gainNode.gain.value = 0.05; // Quieter
            
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.05); // Very short beep
        } catch (e) {
            // Silent fail
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
    }
}

// Make available globally
window.InstantScanner = InstantScanner;