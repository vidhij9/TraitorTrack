/**
 * Instant QR Scanner - Ultra-optimized for speed and consistency
 * Target: < 1 second scan time, 100+ concurrent users
 */

class InstantScanner {
    constructor(containerId, onSuccess) {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.scanning = false;
        this.lastScan = '';
        this.scanCount = 0;
        this.torchSupported = false;
        this.torchEnabled = false;
        
        // Optimized settings for detection accuracy
        this.frameSkip = 0;
        this.targetFPS = 30; // Balanced FPS for quality
        this.scanRegionSize = 0.7; // Larger scan region
        this.lastFrameTime = performance.now();
        this.fpsFrames = [];
        this.processCanvas = null;
        this.processCtx = null;
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div style="position:relative;width:100%;height:400px;background:#000;overflow:hidden;border-radius:8px;">
                <video id="qr-video" style="width:100%;height:100%;object-fit:cover;" muted autoplay playsinline></video>
                <canvas id="qr-canvas" style="display:none;"></canvas>
                
                <!-- Optimized scan region indicator -->
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:200px;height:200px;border:2px solid #0f0;opacity:0.8;">
                    <div style="position:absolute;top:-2px;left:-2px;width:20px;height:20px;border-top:4px solid #0f0;border-left:4px solid #0f0;"></div>
                    <div style="position:absolute;top:-2px;right:-2px;width:20px;height:20px;border-top:4px solid #0f0;border-right:4px solid #0f0;"></div>
                    <div style="position:absolute;bottom:-2px;left:-2px;width:20px;height:20px;border-bottom:4px solid #0f0;border-left:4px solid #0f0;"></div>
                    <div style="position:absolute;bottom:-2px;right:-2px;width:20px;height:20px;border-bottom:4px solid #0f0;border-right:4px solid #0f0;"></div>
                </div>
                
                <div id="scan-status" style="position:absolute;bottom:10px;left:0;right:0;text-align:center;color:#0f0;font-weight:bold;font-size:14px;background:rgba(0,0,0,0.7);padding:8px;">
                    Initializing...
                </div>
                
                <!-- Torch button -->
                <button id="torch-toggle" style="position:absolute;top:10px;right:10px;padding:10px 15px;background:rgba(255,255,255,0.9);border:none;border-radius:5px;cursor:pointer;display:none;">
                    💡 Light
                </button>
            </div>
        `;
        
        this.video = document.getElementById('qr-video');
        this.canvas = document.getElementById('qr-canvas');
        this.ctx = this.canvas.getContext('2d', { 
            willReadFrequently: true,
            alpha: false,
            desynchronized: true 
        });
        this.status = document.getElementById('scan-status');
        
        this.startCamera();
        this.setupTorchButton();
    }
    
    async startCamera() {
        try {
            // Request camera with optimal settings for speed
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280 },  // Higher resolution for better detection
                    height: { ideal: 720 },
                    frameRate: { ideal: 30 },  // Balanced FPS
                    // Add focus constraints
                    focusMode: { ideal: 'continuous' },
                    focusDistance: { ideal: 0.3 },  // Medium distance focus
                    exposureMode: { ideal: 'continuous' },
                    whiteBalanceMode: { ideal: 'continuous' }
                }
            };
            
            const stream = await navigator.mediaDevices.getUserMedia(constraints)
                .catch(() => navigator.mediaDevices.getUserMedia({ video: true }));
            
            this.video.srcObject = stream;
            
            // Apply enhanced camera optimizations for better focus and lighting
            const track = stream.getVideoTracks()[0];
            if (track) {
                const capabilities = track.getCapabilities ? track.getCapabilities() : {};
                console.log('Camera capabilities:', capabilities);
                
                // Apply multiple constraint attempts for better compatibility
                const constraintSets = [
                    // Best quality settings
                    {
                        advanced: [
                            { focusMode: 'continuous' },
                            { focusDistance: 0.15 },  // Closer focus for torch scanning
                            { exposureMode: 'continuous' },
                            { exposureCompensation: -1 },  // Reduce exposure
                            { whiteBalanceMode: 'continuous' },
                            { iso: 100 },  // Lower ISO to reduce noise with torch
                            { brightness: 100 },  // Reduced brightness
                            { contrast: 140 },  // Higher contrast
                            { saturation: 100 },
                            { sharpness: 140 }  // Better edge detection
                        ]
                    },
                    // Fallback settings
                    {
                        focusMode: 'continuous',
                        exposureMode: 'continuous',
                        whiteBalanceMode: 'continuous'
                    },
                    // Minimal settings
                    { focusMode: 'continuous' }
                ];
                
                for (const constraints of constraintSets) {
                    try {
                        await track.applyConstraints(constraints);
                        console.log('Applied camera constraints:', constraints);
                        break;
                    } catch (e) {
                        console.log('Constraint set failed, trying next:', e.message);
                    }
                }
                
                // Check and enable torch if available
                if (capabilities.torch) {
                    this.torchSupported = true;
                    console.log('Torch/flashlight available');
                }
            }
            
            // Start scanning immediately
            await this.video.play();
            this.status.textContent = 'Ready - Point at QR Code';
            
            // Set higher resolution canvas for better detection
            this.canvas.width = 1280;
            this.canvas.height = 720;
            
            // Create processing canvas for image enhancement
            this.processCanvas = document.createElement('canvas');
            this.processCanvas.width = 800;
            this.processCanvas.height = 600;
            this.processCtx = this.processCanvas.getContext('2d', {
                willReadFrequently: true,
                alpha: false
            });
            
            this.startScanning();
            
        } catch (err) {
            console.error('Camera error:', err);
            this.status.textContent = 'Camera Error - Check Permissions';
            this.status.style.color = '#f00';
        }
    }
    
    startScanning() {
        if (this.scanning) return;
        this.scanning = true;
        this.status.textContent = 'Scanning...';
        this.scanLoop();
    }
    
    scanLoop() {
        if (!this.scanning) return;
        
        // Track FPS
        const currentTime = performance.now();
        const deltaTime = currentTime - this.lastFrameTime;
        this.lastFrameTime = currentTime;
        
        if (this.fpsFrames.length < 30) {
            this.fpsFrames.push(1000 / deltaTime);
        } else {
            this.fpsFrames.shift();
            this.fpsFrames.push(1000 / deltaTime);
        }
        
        // NO FRAME SKIPPING - scan every frame for maximum speed
        
        try {
            // Check if video is ready
            if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
                // Draw only center region for faster processing
                const vw = this.video.videoWidth;
                const vh = this.video.videoHeight;
                
                if (vw && vh) {
                    // Draw video to canvas
                    this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                    
                    // Multi-strategy scanning for better detection
                    let detected = false;
                    
                    // Strategy 1: Try direct scan first (works better with torch)
                    if (!detected) {
                        const fullData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
                        
                        // Direct scan without enhancement (best for torch)
                        let code = jsQR(fullData.data, fullData.width, fullData.height, {
                            inversionAttempts: 'attemptBoth'  // Try both normal and inverted
                        });
                        
                        if (code && code.data) {
                            this.handleScan(code.data);
                            detected = true;
                        } else if (this.scanCount % 2 === 0) {
                            // Only enhance if direct scan fails
                            const enhanced = this.enhanceForTorch(fullData);
                            code = jsQR(enhanced.data, enhanced.width, enhanced.height, {
                                inversionAttempts: 'dontInvert'  // Already processed
                            });
                            
                            if (code && code.data) {
                                this.handleScan(code.data);
                                detected = true;
                            }
                        }
                    }
                    
                    // Strategy 2: Center region with contrast enhancement
                    if (!detected) {
                        const regionSize = Math.floor(this.canvas.width * 0.7);  // Larger scan region
                        const offsetX = Math.floor((this.canvas.width - regionSize) / 2);
                        const offsetY = Math.floor((this.canvas.height - regionSize) / 2);
                        
                        // Draw to process canvas for enhancement
                        this.processCtx.drawImage(
                            this.canvas, 
                            offsetX, offsetY, regionSize, regionSize,
                            0, 0, this.processCanvas.width, this.processCanvas.height
                        );
                        
                        const processData = this.processCtx.getImageData(
                            0, 0, this.processCanvas.width, this.processCanvas.height
                        );
                        
                        // Try without enhancement first
                        let code = jsQR(processData.data, processData.width, processData.height, {
                            inversionAttempts: 'attemptBoth'  // Try both
                        });
                        
                        if (!code || !code.data) {
                            // Apply adaptive enhancement only if needed
                            this.adaptiveEnhance(processData);
                            code = jsQR(processData.data, processData.width, processData.height, {
                                inversionAttempts: 'dontInvert'  // Already processed
                            });
                        }
                        
                        if (code && code.data) {
                            this.handleScan(code.data);
                            detected = true;
                        }
                    }
                    
                    // Strategy 3: Multiple small regions for tiny QR codes
                    if (!detected && this.scanCount % 5 === 0) {
                        const regions = [
                            { x: 0.25, y: 0.25 },  // Top-left
                            { x: 0.5, y: 0.25 },   // Top-center
                            { x: 0.75, y: 0.25 },  // Top-right
                            { x: 0.25, y: 0.5 },   // Middle-left
                            { x: 0.5, y: 0.5 },    // Center
                            { x: 0.75, y: 0.5 },   // Middle-right
                            { x: 0.25, y: 0.75 },  // Bottom-left
                            { x: 0.5, y: 0.75 },   // Bottom-center
                            { x: 0.75, y: 0.75 }   // Bottom-right
                        ];
                        
                        const regionSize = Math.floor(this.canvas.width * 0.3);
                        
                        for (const region of regions) {
                            if (detected) break;
                            
                            const x = Math.floor(this.canvas.width * region.x - regionSize/2);
                            const y = Math.floor(this.canvas.height * region.y - regionSize/2);
                            
                            if (x >= 0 && y >= 0 && x + regionSize <= this.canvas.width && y + regionSize <= this.canvas.height) {
                                const regionData = this.ctx.getImageData(x, y, regionSize, regionSize);
                                
                                const code = jsQR(regionData.data, regionData.width, regionData.height, {
                                    inversionAttempts: 'onlyInvert'  // Try inverted for damaged codes
                                });
                                
                                if (code && code.data) {
                                    this.handleScan(code.data);
                                    detected = true;
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        } catch (e) {
            // Silently continue
        }
        
        this.scanCount++;
        
        // Continue scanning
        requestAnimationFrame(() => this.scanLoop());
    }
    
    // Enhanced processing specifically for torch/flash conditions
    enhanceForTorch(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const len = data.length;
        
        // Detect overexposure from torch
        let overexposedPixels = 0;
        let avgBrightness = 0;
        
        for (let i = 0; i < len; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            avgBrightness += gray;
            if (gray > 220) overexposedPixels++;
        }
        
        avgBrightness /= (len / 4);
        const overexposureRatio = overexposedPixels / (len / 4);
        
        if (overexposureRatio > 0.2) {
            // Heavy torch compensation
            for (let i = 0; i < len; i += 4) {
                // Reduce all channels significantly
                const r = Math.min(255, data[i] * 0.6);
                const g = Math.min(255, data[i+1] * 0.6);
                const b = Math.min(255, data[i+2] * 0.6);
                
                const gray = 0.299 * r + 0.587 * g + 0.114 * b;
                
                // Strong binarization for torch
                const value = gray < 110 ? 0 : gray > 140 ? 255 : 128;
                
                data[i] = data[i+1] = data[i+2] = value;
            }
        } else {
            // Standard binarization
            const threshold = avgBrightness * 0.9;
            
            for (let i = 0; i < len; i += 4) {
                const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
                const value = gray > threshold ? 255 : 0;
                data[i] = data[i+1] = data[i+2] = value;
            }
        }
        
        return { data, width: imageData.width, height: imageData.height };
    }
    
    // Image enhancement for better QR detection
    enhanceImageQuality(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const len = data.length;
        
        // Calculate histogram for auto-brightness
        const histogram = new Array(256).fill(0);
        for (let i = 0; i < len; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            histogram[Math.floor(gray)]++;
        }
        
        // Find optimal brightness range
        let cumulative = 0;
        let minVal = 0, maxVal = 255;
        const totalPixels = len / 4;
        
        for (let i = 0; i < 256; i++) {
            cumulative += histogram[i];
            if (cumulative > totalPixels * 0.05) {
                minVal = i;
                break;
            }
        }
        
        cumulative = 0;
        for (let i = 255; i >= 0; i--) {
            cumulative += histogram[i];
            if (cumulative > totalPixels * 0.05) {
                maxVal = i;
                break;
            }
        }
        
        // Apply auto-levels and contrast
        const range = maxVal - minVal || 1;
        const contrastFactor = 255 / range;
        
        for (let i = 0; i < len; i += 4) {
            // Convert to grayscale
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            
            // Apply auto-levels
            let adjusted = (gray - minVal) * contrastFactor;
            
            // Apply slight sharpening
            adjusted = adjusted * 1.1 - 0.05 * 255;
            
            // Clamp and set
            adjusted = Math.max(0, Math.min(255, adjusted));
            data[i] = data[i+1] = data[i+2] = adjusted;
        }
        
        return { data, width: imageData.width, height: imageData.height };
    }
    
    // Adaptive enhancement for varying lighting conditions
    adaptiveEnhance(imageData) {
        const data = imageData.data;
        const len = data.length;
        
        // Apply adaptive thresholding for better contrast
        for (let i = 0; i < len; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            
            // Adaptive threshold based on local area
            const threshold = 128;  // Simple threshold, could be made adaptive
            const value = gray > threshold ? 255 : 0;
            
            data[i] = data[i+1] = data[i+2] = value;
        }
    }
    
    handleScan(data) {
        // Deduplicate
        if (data === this.lastScan) return;
        
        const now = Date.now();
        if (this.lastScanTime && (now - this.lastScanTime) < 300) return;  // Slightly longer delay for stability
        
        this.lastScan = data;
        this.lastScanTime = now;
        
        // Visual feedback
        this.status.textContent = '✓ Scanned!';
        this.status.style.color = '#0f0';
        
        // Audio feedback
        try {
            const beep = new Audio('data:audio/wav;base64,UklGRl4GAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YToGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUand7blmFgU7k9n1unEiBC13yO/eizEIHWq+8+OWT');
            beep.play();
        } catch {}
        
        // Shorter haptic feedback
        if (navigator.vibrate) navigator.vibrate(50);
        
        // Callback
        if (this.onSuccess) {
            this.onSuccess(data);
        }
        
        // Faster reset for continuous scanning
        setTimeout(() => {
            this.status.textContent = 'Scanning...';
            this.status.style.color = '#0f0';
        }, 500);
    }
    
    setupTorchButton() {
        const torchBtn = document.getElementById('torch-toggle');
        if (torchBtn) {
            torchBtn.addEventListener('click', () => this.toggleTorch());
        }
    }
    
    async toggleTorch() {
        if (!this.torchSupported || !this.video || !this.video.srcObject) return;
        
        const track = this.video.srcObject.getVideoTracks()[0];
        if (!track) return;
        
        this.torchEnabled = !this.torchEnabled;
        
        try {
            // Adjust exposure when toggling torch
            if (this.torchEnabled) {
                // Reduce exposure for torch
                await track.applyConstraints({
                    advanced: [
                        { torch: true },
                        { exposureCompensation: -2 },
                        { brightness: 80 }
                    ]
                });
            } else {
                // Normal exposure without torch
                await track.applyConstraints({
                    advanced: [
                        { torch: false },
                        { exposureCompensation: 0 },
                        { brightness: 128 }
                    ]
                });
            }
            
            const torchBtn = document.getElementById('torch-toggle');
            if (torchBtn) {
                torchBtn.style.background = this.torchEnabled ? '#ffd700' : 'rgba(255,255,255,0.9)';
                torchBtn.textContent = this.torchEnabled ? '💡 Light ON' : '💡 Light';
            }
            
            console.log('Torch toggled:', this.torchEnabled);
        } catch (e) {
            console.log('Failed to toggle torch:', e);
        }
    }
    
    stop() {
        this.scanning = false;
        if (this.video && this.video.srcObject) {
            // Turn off torch before stopping
            if (this.torchEnabled) {
                this.toggleTorch();
            }
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
    }
}

// Fallback scanner using QR Scanner library if jsQR fails
class QRScannerFallback {
    constructor(containerId, onSuccess) {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.init();
    }
    
    init() {
        // Load QR Scanner library dynamically
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/qr-scanner@1.4.2/qr-scanner.umd.min.js';
        script.onload = () => this.setupScanner();
        document.head.appendChild(script);
    }
    
    setupScanner() {
        this.container.innerHTML = `
            <video id="qr-video-fallback" style="width:100%;height:400px;object-fit:cover;border-radius:8px;"></video>
        `;
        
        const video = document.getElementById('qr-video-fallback');
        
        // Use QR Scanner library for better performance
        this.qrScanner = new QrScanner(
            video,
            result => this.onSuccess(result.data),
            {
                preferredCamera: 'environment',
                highlightScanRegion: true,
                highlightCodeOutline: true,
                maxScansPerSecond: 10
            }
        );
        
        this.qrScanner.start();
    }
    
    stop() {
        if (this.qrScanner) {
            this.qrScanner.stop();
        }
    }
}

window.InstantScanner = InstantScanner;
window.QRScannerFallback = QRScannerFallback;