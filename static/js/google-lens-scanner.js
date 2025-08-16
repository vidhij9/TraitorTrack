/**
 * Google Lens-like QR Scanner with Multi-Engine Detection
 * Handles worst-case scenarios: blur, damage, poor lighting, any angle
 */

class GoogleLensScanner {
    constructor(videoElement, options = {}) {
        this.video = videoElement;
        this.canvas = document.createElement('canvas');
        this.context = this.canvas.getContext('2d');
        
        // Configuration for extreme conditions
        this.config = {
            fps: options.fps || 30,
            scanRegion: options.scanRegion || { x: 0, y: 0, width: 1, height: 1 },
            multiEngine: options.multiEngine !== false,
            enhanceImage: options.enhanceImage !== false,
            adaptiveScan: options.adaptiveScan !== false,
            ...options
        };
        
        this.isScanning = false;
        this.lastScan = null;
        this.scanAttempts = 0;
        this.engines = [];
        
        // Performance metrics
        this.performance = {
            scansPerSecond: 0,
            successRate: 0,
            totalScans: 0,
            successfulScans: 0
        };
        
        // Initialize engines
        this.initializeEngines();
    }
    
    async initializeEngines() {
        // Load multiple QR detection engines
        try {
            // Primary engine: qr-scanner (fastest)
            if (typeof QrScanner !== 'undefined') {
                this.engines.push({
                    name: 'QrScanner',
                    scan: async (imageData) => {
                        return await QrScanner.scanImage(imageData, {
                            returnDetailedScanResult: true,
                            alsoTryWithoutScanRegion: true
                        });
                    }
                });
            }
        } catch (e) {
            console.warn('QrScanner not available:', e);
        }
        
        // Fallback engine: jsQR (reliable)
        if (typeof jsQR !== 'undefined') {
            this.engines.push({
                name: 'jsQR',
                scan: async (imageData) => {
                    const code = jsQR(
                        imageData.data, 
                        imageData.width, 
                        imageData.height,
                        { inversionAttempts: 'dontInvert' }
                    );
                    return code ? { data: code.data } : null;
                }
            });
        }
        
        // Additional fallback: ZXing
        if (typeof ZXing !== 'undefined') {
            const codeReader = new ZXing.BrowserQRCodeReader();
            this.engines.push({
                name: 'ZXing',
                scan: async (imageData) => {
                    try {
                        const result = await codeReader.decodeFromImageData(imageData);
                        return { data: result.text };
                    } catch (e) {
                        return null;
                    }
                }
            });
        }
    }
    
    /**
     * Enhanced image preprocessing for worst-case scenarios
     */
    preprocessImage(imageData) {
        const data = imageData.data;
        const width = imageData.width;
        const height = imageData.height;
        
        // Apply multiple enhancement techniques
        
        // 1. Adaptive threshold for better contrast
        this.applyAdaptiveThreshold(data, width, height);
        
        // 2. Sharpen filter for blurred codes
        this.applySharpenFilter(data, width, height);
        
        // 3. Denoise for crushed/damaged codes
        this.applyDenoising(data, width, height);
        
        // 4. Contrast enhancement
        this.enhanceContrast(data);
        
        return imageData;
    }
    
    applyAdaptiveThreshold(data, width, height) {
        const blockSize = 15;
        const c = 2;
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = (y * width + x) * 4;
                
                // Calculate local mean
                let sum = 0;
                let count = 0;
                
                for (let dy = -blockSize; dy <= blockSize; dy++) {
                    for (let dx = -blockSize; dx <= blockSize; dx++) {
                        const ny = y + dy;
                        const nx = x + dx;
                        
                        if (ny >= 0 && ny < height && nx >= 0 && nx < width) {
                            const nidx = (ny * width + nx) * 4;
                            sum += data[nidx];
                            count++;
                        }
                    }
                }
                
                const mean = sum / count;
                const threshold = mean - c;
                
                // Apply threshold
                const value = data[idx] > threshold ? 255 : 0;
                data[idx] = data[idx + 1] = data[idx + 2] = value;
            }
        }
    }
    
    applySharpenFilter(data, width, height) {
        const kernel = [
            0, -1, 0,
            -1, 5, -1,
            0, -1, 0
        ];
        
        const temp = new Uint8ClampedArray(data);
        
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                const idx = (y * width + x) * 4;
                let r = 0, g = 0, b = 0;
                
                for (let ky = -1; ky <= 1; ky++) {
                    for (let kx = -1; kx <= 1; kx++) {
                        const kidx = ((y + ky) * width + (x + kx)) * 4;
                        const kval = kernel[(ky + 1) * 3 + (kx + 1)];
                        
                        r += temp[kidx] * kval;
                        g += temp[kidx + 1] * kval;
                        b += temp[kidx + 2] * kval;
                    }
                }
                
                data[idx] = Math.max(0, Math.min(255, r));
                data[idx + 1] = Math.max(0, Math.min(255, g));
                data[idx + 2] = Math.max(0, Math.min(255, b));
            }
        }
    }
    
    applyDenoising(data, width, height) {
        // Median filter for noise reduction
        const temp = new Uint8ClampedArray(data);
        const windowSize = 3;
        
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                const values = [];
                
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        const idx = ((y + dy) * width + (x + dx)) * 4;
                        values.push(temp[idx]);
                    }
                }
                
                values.sort((a, b) => a - b);
                const median = values[Math.floor(values.length / 2)];
                
                const idx = (y * width + x) * 4;
                data[idx] = data[idx + 1] = data[idx + 2] = median;
            }
        }
    }
    
    enhanceContrast(data) {
        // Find min and max values
        let min = 255, max = 0;
        
        for (let i = 0; i < data.length; i += 4) {
            const gray = data[i];
            min = Math.min(min, gray);
            max = Math.max(max, gray);
        }
        
        // Stretch contrast
        const range = max - min;
        if (range > 0) {
            for (let i = 0; i < data.length; i += 4) {
                const value = ((data[i] - min) * 255) / range;
                data[i] = data[i + 1] = data[i + 2] = value;
            }
        }
    }
    
    /**
     * Multi-angle scanning with rotation attempts
     */
    async scanWithRotations(imageData) {
        const angles = [0, 90, 180, 270, 45, -45];
        
        for (const angle of angles) {
            const rotated = this.rotateImage(imageData, angle);
            
            for (const engine of this.engines) {
                try {
                    const result = await engine.scan(rotated);
                    if (result && result.data) {
                        console.log(`Success with ${engine.name} at ${angle}°`);
                        return result;
                    }
                } catch (e) {
                    // Continue with next engine
                }
            }
        }
        
        return null;
    }
    
    rotateImage(imageData, angle) {
        if (angle === 0) return imageData;
        
        const rad = (angle * Math.PI) / 180;
        const cos = Math.cos(rad);
        const sin = Math.sin(rad);
        
        const width = imageData.width;
        const height = imageData.height;
        
        // Calculate new dimensions
        const newWidth = Math.abs(width * cos) + Math.abs(height * sin);
        const newHeight = Math.abs(width * sin) + Math.abs(height * cos);
        
        const rotated = new ImageData(
            Math.ceil(newWidth),
            Math.ceil(newHeight)
        );
        
        const cx = width / 2;
        const cy = height / 2;
        const ncx = newWidth / 2;
        const ncy = newHeight / 2;
        
        for (let y = 0; y < newHeight; y++) {
            for (let x = 0; x < newWidth; x++) {
                // Reverse rotation to find source pixel
                const sx = cos * (x - ncx) + sin * (y - ncy) + cx;
                const sy = -sin * (x - ncx) + cos * (y - ncy) + cy;
                
                if (sx >= 0 && sx < width && sy >= 0 && sy < height) {
                    const sIdx = (Math.floor(sy) * width + Math.floor(sx)) * 4;
                    const dIdx = (y * newWidth + x) * 4;
                    
                    rotated.data[dIdx] = imageData.data[sIdx];
                    rotated.data[dIdx + 1] = imageData.data[sIdx + 1];
                    rotated.data[dIdx + 2] = imageData.data[sIdx + 2];
                    rotated.data[dIdx + 3] = imageData.data[sIdx + 3];
                }
            }
        }
        
        return rotated;
    }
    
    /**
     * Main scanning function with multi-engine fallback
     */
    async scan() {
        if (!this.isScanning) return null;
        
        try {
            // Capture frame from video
            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;
            this.context.drawImage(this.video, 0, 0);
            
            let imageData = this.context.getImageData(
                0, 0, 
                this.canvas.width, 
                this.canvas.height
            );
            
            this.performance.totalScans++;
            
            // Try normal scan first
            for (const engine of this.engines) {
                try {
                    const result = await engine.scan(imageData);
                    if (result && result.data) {
                        this.onSuccess(result);
                        return result;
                    }
                } catch (e) {
                    // Continue with next engine
                }
            }
            
            // If normal scan fails, try with preprocessing
            if (this.config.enhanceImage) {
                imageData = this.preprocessImage(imageData);
                
                for (const engine of this.engines) {
                    try {
                        const result = await engine.scan(imageData);
                        if (result && result.data) {
                            this.onSuccess(result);
                            return result;
                        }
                    } catch (e) {
                        // Continue with next engine
                    }
                }
            }
            
            // If still no result, try rotation scanning
            if (this.config.adaptiveScan) {
                const result = await this.scanWithRotations(imageData);
                if (result) {
                    this.onSuccess(result);
                    return result;
                }
            }
            
        } catch (error) {
            console.error('Scan error:', error);
        }
        
        return null;
    }
    
    onSuccess(result) {
        this.performance.successfulScans++;
        this.performance.successRate = 
            (this.performance.successfulScans / this.performance.totalScans) * 100;
        
        // Haptic feedback if available
        if (navigator.vibrate) {
            navigator.vibrate(100);
        }
        
        // Audio feedback
        this.playSuccessSound();
    }
    
    playSuccessSound() {
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
    }
    
    async start() {
        this.isScanning = true;
        
        // Start scanning loop
        const scanLoop = async () => {
            if (!this.isScanning) return;
            
            const result = await this.scan();
            if (result && this.onScanSuccess) {
                this.onScanSuccess(result);
            }
            
            // Adaptive frame rate based on performance
            const delay = this.performance.successRate < 50 ? 50 : 100;
            setTimeout(scanLoop, delay);
        };
        
        scanLoop();
    }
    
    stop() {
        this.isScanning = false;
    }
    
    getPerformanceStats() {
        return {
            ...this.performance,
            engines: this.engines.map(e => e.name)
        };
    }
}

// Export for use in other files
window.GoogleLensScanner = GoogleLensScanner;