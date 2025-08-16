/**
 * Extreme QR Scanner - Handles worst case scenarios
 * Blur, dim lights, crushed plastic, any condition
 */

class ExtremeScanner {
    constructor(containerId, onSuccess) {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.lastScan = 0;
        this.scanning = false;
        
        // Camera elements
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        
        // Processing canvases for different techniques
        this.processCanvases = [];
        for(let i = 0; i < 3; i++) {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d', { willReadFrequently: true });
            this.processCanvases.push({ canvas, ctx });
        }
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div style="position:relative;width:100%;height:450px;background:#000;overflow:hidden;border-radius:8px;">
                <video id="extreme-video" style="width:100%;height:100%;object-fit:cover;" playsinline autoplay muted></video>
                <canvas id="extreme-canvas" style="display:none;"></canvas>
                
                <!-- Aggressive scanning indicator -->
                <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;">
                    <div style="width:280px;height:280px;position:relative;">
                        <!-- Multi-layer scan box for visibility -->
                        <div style="position:absolute;inset:0;border:3px solid #0f0;opacity:0.9;box-shadow:0 0 20px #0f0;"></div>
                        <div style="position:absolute;inset:-5px;border:1px solid #0f0;opacity:0.5;"></div>
                        
                        <!-- Corner markers -->
                        <div style="position:absolute;top:-3px;left:-3px;width:40px;height:40px;border-top:4px solid #0f0;border-left:4px solid #0f0;"></div>
                        <div style="position:absolute;top:-3px;right:-3px;width:40px;height:40px;border-top:4px solid #0f0;border-right:4px solid #0f0;"></div>
                        <div style="position:absolute;bottom:-3px;left:-3px;width:40px;height:40px;border-bottom:4px solid #0f0;border-left:4px solid #0f0;"></div>
                        <div style="position:absolute;bottom:-3px;right:-3px;width:40px;height:40px;border-bottom:4px solid #0f0;border-right:4px solid #0f0;"></div>
                    </div>
                </div>
                
                <!-- Status with processing indicator -->
                <div id="extreme-status" style="position:absolute;bottom:15px;left:0;right:0;text-align:center;">
                    <div style="background:rgba(0,0,0,0.7);display:inline-block;padding:10px 20px;border-radius:5px;">
                        <span style="color:#fff;font-size:18px;font-weight:bold;">SCANNING...</span>
                        <div id="process-indicator" style="margin-top:5px;color:#0f0;font-size:12px;">Processing: Normal</div>
                    </div>
                </div>
            </div>
        `;
        
        this.video = document.getElementById('extreme-video');
        this.canvas = document.getElementById('extreme-canvas');
        this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
        
        this.startCamera();
    }
    
    async startCamera() {
        try {
            // Try high quality camera first
            let stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1920 },
                    height: { ideal: 1080 }
                }
            }).catch(() => {
                // Fallback to any camera
                return navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'environment' }
                });
            }).catch(() => {
                return navigator.mediaDevices.getUserMedia({ video: true });
            });
            
            this.video.srcObject = stream;
            
            this.video.onloadedmetadata = () => {
                // Use full resolution for better scanning
                this.canvas.width = this.video.videoWidth;
                this.canvas.height = this.video.videoHeight;
                
                // Setup processing canvases
                this.processCanvases.forEach(pc => {
                    pc.canvas.width = this.canvas.width;
                    pc.canvas.height = this.canvas.height;
                });
                
                this.scanning = true;
                this.updateStatus('SCANNING...', 'Normal');
                this.aggressiveScan();
            };
        } catch (err) {
            this.updateStatus('CAMERA ERROR', 'Failed');
            console.error('Camera error:', err);
        }
    }
    
    aggressiveScan() {
        if (!this.scanning) return;
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            // Original image
            this.ctx.drawImage(this.video, 0, 0);
            const originalData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // Try original first (fastest)
            if (this.tryDecode(originalData, 'Normal')) {
                setTimeout(() => this.aggressiveScan(), 50);
                return;
            }
            
            // Enhanced contrast for dim lights
            const enhanced = this.enhanceContrast(originalData);
            if (this.tryDecode(enhanced, 'Enhanced')) {
                setTimeout(() => this.aggressiveScan(), 50);
                return;
            }
            
            // Sharpen for blur
            const sharpened = this.sharpenImage(originalData);
            if (this.tryDecode(sharpened, 'Sharpened')) {
                setTimeout(() => this.aggressiveScan(), 50);
                return;
            }
            
            // Binary threshold for crushed/damaged codes
            const binary = this.binaryThreshold(originalData);
            if (this.tryDecode(binary, 'Binary')) {
                setTimeout(() => this.aggressiveScan(), 50);
                return;
            }
            
            // Adaptive threshold for extreme cases
            const adaptive = this.adaptiveThreshold(originalData);
            if (this.tryDecode(adaptive, 'Adaptive')) {
                setTimeout(() => this.aggressiveScan(), 50);
                return;
            }
        }
        
        // Continuous aggressive scanning
        requestAnimationFrame(() => this.aggressiveScan());
    }
    
    tryDecode(imageData, mode) {
        this.updateStatus('SCANNING...', mode);
        
        if (typeof jsQR !== 'undefined') {
            // Try both normal and inverted
            const code = jsQR(imageData.data, imageData.width, imageData.height, {
                inversionAttempts: 'attemptBoth'
            });
            
            if (code && code.data) {
                this.handleSuccess(code.data);
                return true;
            }
        }
        return false;
    }
    
    enhanceContrast(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const len = data.length;
        
        // Find min and max for stretching
        let min = 255, max = 0;
        for (let i = 0; i < len; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            min = Math.min(min, gray);
            max = Math.max(max, gray);
        }
        
        const range = max - min || 1;
        
        // Stretch contrast
        for (let i = 0; i < len; i += 4) {
            data[i] = ((data[i] - min) * 255 / range);
            data[i+1] = ((data[i+1] - min) * 255 / range);
            data[i+2] = ((data[i+2] - min) * 255 / range);
        }
        
        return new ImageData(data, imageData.width, imageData.height);
    }
    
    sharpenImage(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const width = imageData.width;
        const height = imageData.height;
        const output = new Uint8ClampedArray(data);
        
        // Sharpen kernel
        const kernel = [
            0, -1, 0,
            -1, 5, -1,
            0, -1, 0
        ];
        
        for (let y = 1; y < height - 1; y++) {
            for (let x = 1; x < width - 1; x++) {
                for (let c = 0; c < 3; c++) {
                    let sum = 0;
                    for (let ky = -1; ky <= 1; ky++) {
                        for (let kx = -1; kx <= 1; kx++) {
                            const idx = ((y + ky) * width + (x + kx)) * 4 + c;
                            sum += data[idx] * kernel[(ky + 1) * 3 + (kx + 1)];
                        }
                    }
                    const idx = (y * width + x) * 4 + c;
                    output[idx] = Math.min(255, Math.max(0, sum));
                }
            }
        }
        
        return new ImageData(output, width, height);
    }
    
    binaryThreshold(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const len = data.length;
        
        // Calculate threshold using Otsu's method
        const histogram = new Array(256).fill(0);
        for (let i = 0; i < len; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            histogram[Math.floor(gray)]++;
        }
        
        let sum = 0;
        for (let i = 0; i < 256; i++) sum += i * histogram[i];
        
        let sumB = 0, wB = 0, wF = 0;
        let varMax = 0, threshold = 0;
        const total = len / 4;
        
        for (let t = 0; t < 256; t++) {
            wB += histogram[t];
            if (wB === 0) continue;
            
            wF = total - wB;
            if (wF === 0) break;
            
            sumB += t * histogram[t];
            const mB = sumB / wB;
            const mF = (sum - sumB) / wF;
            
            const varBetween = wB * wF * (mB - mF) * (mB - mF);
            
            if (varBetween > varMax) {
                varMax = varBetween;
                threshold = t;
            }
        }
        
        // Apply threshold
        for (let i = 0; i < len; i += 4) {
            const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2];
            const val = gray > threshold ? 255 : 0;
            data[i] = data[i+1] = data[i+2] = val;
        }
        
        return new ImageData(data, imageData.width, imageData.height);
    }
    
    adaptiveThreshold(imageData) {
        const data = new Uint8ClampedArray(imageData.data);
        const width = imageData.width;
        const height = imageData.height;
        const output = new Uint8ClampedArray(data);
        
        const blockSize = 15;
        const c = 10;
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                let sum = 0, count = 0;
                
                // Calculate local mean
                for (let dy = -blockSize; dy <= blockSize; dy++) {
                    for (let dx = -blockSize; dx <= blockSize; dx++) {
                        const ny = y + dy;
                        const nx = x + dx;
                        if (ny >= 0 && ny < height && nx >= 0 && nx < width) {
                            const idx = (ny * width + nx) * 4;
                            sum += 0.299 * data[idx] + 0.587 * data[idx+1] + 0.114 * data[idx+2];
                            count++;
                        }
                    }
                }
                
                const mean = sum / count;
                const idx = (y * width + x) * 4;
                const gray = 0.299 * data[idx] + 0.587 * data[idx+1] + 0.114 * data[idx+2];
                const val = gray > (mean - c) ? 255 : 0;
                output[idx] = output[idx+1] = output[idx+2] = val;
            }
        }
        
        return new ImageData(output, width, height);
    }
    
    handleSuccess(data) {
        const now = Date.now();
        if (now - this.lastScan < 1000) return;
        this.lastScan = now;
        
        this.updateStatus('SCANNED!', 'Success');
        
        // Strong feedback
        try {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBi+Gyffo');
            audio.volume = 0.5;
            audio.play();
        } catch(e) {}
        
        if (navigator.vibrate) navigator.vibrate([200, 100, 200]);
        
        if (this.onSuccess) this.onSuccess(data);
        
        setTimeout(() => this.updateStatus('SCANNING...', 'Normal'), 1500);
    }
    
    updateStatus(text, mode) {
        const status = document.querySelector('#extreme-status span');
        const indicator = document.getElementById('process-indicator');
        if (status) status.textContent = text;
        if (indicator) indicator.textContent = `Processing: ${mode}`;
    }
    
    stop() {
        this.scanning = false;
        if (this.video && this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
    }
}

window.ExtremeScanner = ExtremeScanner;