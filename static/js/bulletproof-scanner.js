/**
 * Bulletproof QR Scanner - Maximum Reliability
 * ============================================
 * Comprehensive scanning that tries everything to detect QR codes
 */

class BulletproofScanner {
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
        this.scanAttempts = 0;
        this.maxAttempts = 10;
        
        // Multiple canvases for different processing strategies
        this.canvases = [];
        this.contexts = [];
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div style="position:relative;width:100%;max-width:640px;margin:0 auto;">
                <video id="bulletproof-video" autoplay playsinline muted 
                       style="width:100%;height:400px;object-fit:cover;border-radius:8px;background:#000;"></video>
                
                <!-- Multiple hidden canvases for processing -->
                <canvas id="main-canvas" style="display:none;"></canvas>
                <canvas id="gray-canvas" style="display:none;"></canvas>
                <canvas id="enhanced-canvas" style="display:none;"></canvas>
                <canvas id="threshold-canvas" style="display:none;"></canvas>
                
                <!-- Scan overlay -->
                <div style="position:absolute;top:0;left:0;right:0;bottom:0;pointer-events:none;">
                    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:250px;height:250px;border:3px solid #0f0;border-radius:8px;">
                        <div style="position:absolute;top:-5px;left:-5px;width:30px;height:30px;border-left:5px solid #0f0;border-top:5px solid #0f0;"></div>
                        <div style="position:absolute;top:-5px;right:-5px;width:30px;height:30px;border-right:5px solid #0f0;border-top:5px solid #0f0;"></div>
                        <div style="position:absolute;bottom:-5px;left:-5px;width:30px;height:30px;border-left:5px solid #0f0;border-bottom:5px solid #0f0;"></div>
                        <div style="position:absolute;bottom:-5px;right:-5px;width:30px;height:30px;border-right:5px solid #0f0;border-bottom:5px solid #0f0;"></div>
                    </div>
                </div>
                
                <!-- Status and controls -->
                <div style="position:absolute;bottom:10px;left:0;right:0;text-align:center;">
                    <div id="scan-status" style="color:#0f0;font-weight:bold;background:rgba(0,0,0,0.8);padding:8px;border-radius:4px;margin-bottom:10px;">
                        Initializing...
                    </div>
                    <button id="torch-toggle" style="padding:10px 20px;background:#ffa500;border:none;border-radius:5px;color:white;font-weight:bold;display:none;">
                        💡 Flash
                    </button>
                </div>
            </div>
        `;
        
        this.setupElements();
        this.startCamera();
    }
    
    setupElements() {
        this.video = document.getElementById('bulletproof-video');
        this.status = document.getElementById('scan-status');
        this.torchBtn = document.getElementById('torch-toggle');
        
        // Setup multiple canvases
        const canvasIds = ['main-canvas', 'gray-canvas', 'enhanced-canvas', 'threshold-canvas'];
        
        canvasIds.forEach(id => {
            const canvas = document.getElementById(id);
            const ctx = canvas.getContext('2d', {
                willReadFrequently: true,
                alpha: false,
                desynchronized: true
            });
            this.canvases.push(canvas);
            this.contexts.push(ctx);
        });
        
        this.canvas = this.canvases[0];
        this.ctx = this.contexts[0];
        
        // Torch toggle
        if (this.torchBtn) {
            this.torchBtn.addEventListener('click', () => this.toggleTorch());
        }
    }
    
    async startCamera() {
        try {
            this.updateStatus('Starting camera...', '#ffa500');
            
            // Try high quality first, then fallback
            const constraints = [
                {
                    video: {
                        facingMode: 'environment',
                        width: { ideal: 1920 },
                        height: { ideal: 1080 },
                        frameRate: { ideal: 30 }
                    }
                },
                {
                    video: {
                        facingMode: 'environment',
                        width: { ideal: 1280 },
                        height: { ideal: 720 },
                        frameRate: { ideal: 30 }
                    }
                },
                {
                    video: { facingMode: 'environment' }
                },
                {
                    video: true
                }
            ];
            
            let stream = null;
            for (const constraint of constraints) {
                try {
                    stream = await navigator.mediaDevices.getUserMedia(constraint);
                    break;
                } catch (e) {
                    console.log('Constraint failed, trying next...');
                }
            }
            
            if (!stream) {
                throw new Error('Could not access camera');
            }
            
            this.stream = stream;
            this.video.srcObject = stream;
            
            await new Promise((resolve, reject) => {
                this.video.onloadedmetadata = () => {
                    this.video.play().then(resolve).catch(reject);
                };
                setTimeout(() => reject(new Error('Video load timeout')), 10000);
            });
            
            // Setup torch if available
            await this.setupTorch();
            
            // Apply optimal camera settings
            await this.optimizeCamera();
            
            this.updateStatus('Camera ready! Point at QR code', '#0f0');
            this.startScanning();
            
        } catch (error) {
            console.error('Camera error:', error);
            this.updateStatus('Camera error: ' + error.message, '#f00');
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
        
        // Try to apply optimal settings
        const settings = [
            {
                focusMode: 'continuous',
                exposureMode: 'continuous',
                whiteBalanceMode: 'continuous'
            },
            {
                advanced: [
                    { focusMode: 'continuous' },
                    { exposureMode: 'continuous' },
                    { whiteBalanceMode: 'continuous' },
                    { focusDistance: 0.3 }
                ]
            }
        ];
        
        for (const setting of settings) {
            try {
                await track.applyConstraints(setting);
                console.log('Applied camera optimization');
                break;
            } catch (e) {
                console.log('Camera setting failed, trying next...');
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
            this.torchBtn.style.background = this.torchEnabled ? '#ff6b35' : '#ffa500';
            
        } catch (e) {
            console.log('Torch toggle failed:', e);
        }
    }
    
    startScanning() {
        if (this.scanning) return;
        this.scanning = true;
        this.updateStatus('Scanning for QR codes...', '#0f0');
        this.scanLoop();
    }
    
    scanLoop() {
        if (!this.scanning || !this.video || this.video.readyState !== 4) {
            if (this.scanning) {
                requestAnimationFrame(() => this.scanLoop());
            }
            return;
        }
        
        try {
            // Update all canvas sizes
            const videoWidth = this.video.videoWidth;
            const videoHeight = this.video.videoHeight;
            
            if (videoWidth > 0 && videoHeight > 0) {
                this.canvases.forEach(canvas => {
                    canvas.width = videoWidth;
                    canvas.height = videoHeight;
                });
                
                // Draw video to main canvas
                this.ctx.drawImage(this.video, 0, 0);
                
                // Try comprehensive scanning
                this.comprehensiveScan();
            }
            
        } catch (error) {
            console.error('Scan error:', error);
        }
        
        // Continue scanning at high frequency
        requestAnimationFrame(() => this.scanLoop());
    }
    
    comprehensiveScan() {
        const strategies = [
            () => this.scanDirect(),           // 1. Direct scan
            () => this.scanGrayscale(),        // 2. Grayscale
            () => this.scanEnhanced(),         // 3. Enhanced contrast
            () => this.scanThreshold(),        // 4. Threshold
            () => this.scanRegions(),          // 5. Multiple regions
            () => this.scanRotated(),          // 6. Rotated
            () => this.scanScaled()            // 7. Different scales
        ];
        
        // Try each strategy
        for (let i = 0; i < strategies.length; i++) {
            try {
                const result = strategies[i]();
                if (result && result.data) {
                    this.handleSuccess(result.data);
                    return true;
                }
            } catch (e) {
                // Continue to next strategy
            }
        }
        
        return false;
    }
    
    scanDirect() {
        // Strategy 1: Direct scan of original image
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        
        return jsQR(imageData.data, imageData.width, imageData.height, {
            inversionAttempts: "attemptBoth"
        });
    }
    
    scanGrayscale() {
        // Strategy 2: Convert to grayscale
        const grayCtx = this.contexts[1];
        grayCtx.drawImage(this.canvas, 0, 0);
        
        const imageData = grayCtx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        
        // Convert to grayscale
        for (let i = 0; i < data.length; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            data[i] = data[i + 1] = data[i + 2] = gray;
        }
        
        return jsQR(data, imageData.width, imageData.height, {
            inversionAttempts: "attemptBoth"
        });
    }
    
    scanEnhanced() {
        // Strategy 3: Enhanced contrast
        const enhancedCtx = this.contexts[2];
        enhancedCtx.drawImage(this.canvas, 0, 0);
        
        const imageData = enhancedCtx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        
        // Enhance contrast
        for (let i = 0; i < data.length; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            const enhanced = ((gray - 128) * 2) + 128;
            const clamped = Math.max(0, Math.min(255, enhanced));
            data[i] = data[i + 1] = data[i + 2] = clamped;
        }
        
        return jsQR(data, imageData.width, imageData.height, {
            inversionAttempts: "dontInvert"
        });
    }
    
    scanThreshold() {
        // Strategy 4: Binary threshold
        const thresholdCtx = this.contexts[3];
        thresholdCtx.drawImage(this.canvas, 0, 0);
        
        const imageData = thresholdCtx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        
        // Calculate average brightness
        let total = 0;
        for (let i = 0; i < data.length; i += 4) {
            total += 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        }
        const threshold = total / (data.length / 4);
        
        // Apply threshold
        for (let i = 0; i < data.length; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
            const value = gray > threshold ? 255 : 0;
            data[i] = data[i + 1] = data[i + 2] = value;
        }
        
        return jsQR(data, imageData.width, imageData.height, {
            inversionAttempts: "dontInvert"
        });
    }
    
    scanRegions() {
        // Strategy 5: Scan multiple regions
        const regions = [
            { x: 0, y: 0, w: 1, h: 1 },           // Full
            { x: 0.1, y: 0.1, w: 0.8, h: 0.8 },   // Center
            { x: 0, y: 0, w: 0.5, h: 0.5 },       // Top-left
            { x: 0.5, y: 0, w: 0.5, h: 0.5 },     // Top-right
            { x: 0, y: 0.5, w: 0.5, h: 0.5 },     // Bottom-left
            { x: 0.5, y: 0.5, w: 0.5, h: 0.5 },   // Bottom-right
            { x: 0.25, y: 0.25, w: 0.5, h: 0.5 }  // Middle
        ];
        
        for (const region of regions) {
            const x = Math.floor(this.canvas.width * region.x);
            const y = Math.floor(this.canvas.height * region.y);
            const w = Math.floor(this.canvas.width * region.w);
            const h = Math.floor(this.canvas.height * region.h);
            
            if (x + w <= this.canvas.width && y + h <= this.canvas.height) {
                const imageData = this.ctx.getImageData(x, y, w, h);
                
                const result = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "attemptBoth"
                });
                
                if (result && result.data) {
                    return result;
                }
            }
        }
        
        return null;
    }
    
    scanRotated() {
        // Strategy 6: Try slight rotations
        const angles = [0, 5, -5, 10, -10];
        
        for (const angle of angles) {
            if (angle === 0) continue; // Already tried direct
            
            const rotatedCtx = this.contexts[1];
            const centerX = this.canvas.width / 2;
            const centerY = this.canvas.height / 2;
            
            rotatedCtx.save();
            rotatedCtx.translate(centerX, centerY);
            rotatedCtx.rotate((angle * Math.PI) / 180);
            rotatedCtx.translate(-centerX, -centerY);
            rotatedCtx.drawImage(this.canvas, 0, 0);
            rotatedCtx.restore();
            
            const imageData = rotatedCtx.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            const result = jsQR(imageData.data, imageData.width, imageData.height, {
                inversionAttempts: "attemptBoth"
            });
            
            if (result && result.data) {
                return result;
            }
        }
        
        return null;
    }
    
    scanScaled() {
        // Strategy 7: Try different scales
        const scales = [1.5, 2.0, 0.75, 0.5];
        
        for (const scale of scales) {
            const scaledCtx = this.contexts[2];
            const scaledWidth = Math.floor(this.canvas.width * scale);
            const scaledHeight = Math.floor(this.canvas.height * scale);
            
            scaledCtx.canvas.width = scaledWidth;
            scaledCtx.canvas.height = scaledHeight;
            
            scaledCtx.drawImage(this.canvas, 0, 0, scaledWidth, scaledHeight);
            
            const imageData = scaledCtx.getImageData(0, 0, scaledWidth, scaledHeight);
            
            const result = jsQR(imageData.data, imageData.width, imageData.height, {
                inversionAttempts: "attemptBoth"
            });
            
            if (result && result.data) {
                return result;
            }
        }
        
        return null;
    }
    
    handleSuccess(qrData) {
        // Prevent duplicates
        const now = Date.now();
        if (qrData === this.lastScan && (now - this.lastScanTime) < 1000) {
            return;
        }
        
        this.lastScan = qrData;
        this.lastScanTime = now;
        
        console.log('QR Code detected:', qrData);
        
        // Visual feedback
        this.updateStatus('✅ QR Code Detected!', '#0f0');
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate([100, 50, 100]);
        }
        
        // Audio feedback
        this.playBeep();
        
        // Callback
        if (this.onSuccess) {
            this.onSuccess(qrData);
        }
        
        // Resume scanning after brief pause
        setTimeout(() => {
            this.updateStatus('Scanning for QR codes...', '#0f0');
        }, 1500);
    }
    
    playBeep() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 1000;
            oscillator.type = 'sine';
            gainNode.gain.value = 0.1;
            
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.15);
        } catch (e) {
            // Silent fail
        }
    }
    
    updateStatus(message, color = '#0f0') {
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
window.BulletproofScanner = BulletproofScanner;