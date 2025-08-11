/**
 * Bulletproof QR Scanner - Works everywhere, every time
 * Multiple approaches, maximum compatibility
 */

class BulletproofQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.scanner = null;
        this.isScanning = false;
        this.onSuccess = null;
        this.retryCount = 0;
        this.maxRetries = 3;
        
        console.log('BulletproofQR: Initializing universal scanner');
        this.initializeUniversalScanner();
    }
    
    async initializeUniversalScanner() {
        this.setupUI();
        
        // Try multiple approaches in sequence
        const approaches = [
            () => this.tryHtml5QrCode(),
            () => this.tryNativeMediaDevices(),
            () => this.tryFileInput(),
            () => this.tryManualEntry()
        ];
        
        for (let i = 0; i < approaches.length; i++) {
            try {
                this.updateStatus(`Trying approach ${i + 1}...`, 'info');
                await approaches[i]();
                console.log(`BulletproofQR: Approach ${i + 1} successful`);
                return;
            } catch (error) {
                console.log(`BulletproofQR: Approach ${i + 1} failed:`, error);
                if (i < approaches.length - 1) {
                    await this.wait(1000);
                }
            }
        }
        
        this.updateStatus('All camera methods failed - Manual entry available', 'warning');
    }
    
    setupUI() {
        this.container.innerHTML = `
            <div class="bulletproof-scanner">
                <div id="${this.containerId}-camera-area" class="camera-area">
                    <div class="loading-indicator">
                        <div class="spinner"></div>
                        <div class="loading-text">Starting camera...</div>
                    </div>
                </div>
                
                <div class="scanner-status" id="scanner-status">
                    <div class="status-icon">📱</div>
                    <div class="status-text">Initializing scanner...</div>
                </div>
                
                <div class="fallback-controls" id="fallback-controls" style="display: none;">
                    <h6>Alternative Methods:</h6>
                    <input type="file" id="file-upload" accept="image/*" class="form-control mb-2">
                    <input type="text" id="manual-input" placeholder="Enter QR code manually" class="form-control mb-2">
                    <button id="submit-manual" class="btn btn-primary btn-sm">Submit</button>
                </div>
            </div>
            
            <style>
                .bulletproof-scanner {
                    width: 100%;
                    min-height: 400px;
                    border-radius: 8px;
                    overflow: hidden;
                    background: #000;
                    position: relative;
                }
                
                .camera-area {
                    width: 100%;
                    height: 400px;
                    position: relative;
                    background: #000;
                }
                
                .loading-indicator {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    text-align: center;
                    color: white;
                }
                
                .spinner {
                    width: 40px;
                    height: 40px;
                    border: 4px solid #333;
                    border-top: 4px solid #007bff;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 15px;
                }
                
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                
                .scanner-status {
                    position: absolute;
                    bottom: 10px;
                    left: 10px;
                    right: 10px;
                    background: rgba(0,0,0,0.8);
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                    text-align: center;
                    font-size: 14px;
                }
                
                .status-icon {
                    font-size: 20px;
                    margin-bottom: 5px;
                }
                
                .fallback-controls {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 0 0 8px 8px;
                }
                
                .status-success {
                    background: rgba(0,255,0,0.8) !important;
                    color: black !important;
                }
                
                .status-error {
                    background: rgba(255,0,0,0.8) !important;
                }
                
                .status-warning {
                    background: rgba(255,165,0,0.8) !important;
                    color: black !important;
                }
            </style>
        `;
        
        this.setupFallbackControls();
    }
    
    setupFallbackControls() {
        // File upload handler
        const fileUpload = document.getElementById('file-upload');
        if (fileUpload) {
            fileUpload.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    this.processFile(file);
                }
            });
        }
        
        // Manual entry handler
        const submitManual = document.getElementById('submit-manual');
        const manualInput = document.getElementById('manual-input');
        
        if (submitManual && manualInput) {
            submitManual.addEventListener('click', () => {
                const value = manualInput.value.trim();
                if (value) {
                    this.handleSuccess(value);
                    manualInput.value = '';
                }
            });
            
            manualInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    submitManual.click();
                }
            });
        }
    }
    
    updateStatus(text, type = 'info') {
        const statusEl = document.getElementById('scanner-status');
        const textEl = statusEl?.querySelector('.status-text');
        const iconEl = statusEl?.querySelector('.status-icon');
        
        if (textEl) textEl.textContent = text;
        
        const icons = {
            info: '📱',
            success: '✅',
            error: '❌',
            warning: '⚠️'
        };
        
        if (iconEl) iconEl.textContent = icons[type] || '📱';
        
        if (statusEl) {
            statusEl.className = `scanner-status status-${type}`;
        }
    }
    
    async tryHtml5QrCode() {
        this.updateStatus('Trying HTML5 QR scanner...', 'info');
        
        // Wait for library to load
        await this.waitForLibrary();
        
        const cameraArea = document.getElementById(`${this.containerId}-camera-area`);
        cameraArea.innerHTML = `<div id="${this.containerId}-html5-reader" style="width: 100%; height: 100%;"></div>`;
        
        this.scanner = new Html5Qrcode(`${this.containerId}-html5-reader`);
        
        // Get cameras
        const cameras = await Html5Qrcode.getCameras();
        if (cameras.length === 0) {
            throw new Error('No cameras found');
        }
        
        // Start with minimal configuration
        const config = {
            fps: 10,
            qrbox: 200,
            aspectRatio: 1.0
        };
        
        await this.scanner.start(
            cameras[0].id,
            config,
            (decodedText) => {
                console.log('HTML5 QR detected:', decodedText);
                this.handleSuccess(decodedText);
            },
            () => {}
        );
        
        this.isScanning = true;
        this.updateStatus('Camera active - Ready to scan!', 'success');
    }
    
    async tryNativeMediaDevices() {
        this.updateStatus('Trying native camera access...', 'info');
        
        const cameraArea = document.getElementById(`${this.containerId}-camera-area`);
        cameraArea.innerHTML = `
            <video id="${this.containerId}-video" autoplay playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>
            <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
        `;
        
        const video = document.getElementById(`${this.containerId}-video`);
        const canvas = document.getElementById(`${this.containerId}-canvas`);
        
        // Request camera access
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment',
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        });
        
        video.srcObject = stream;
        
        // Wait for video to be ready
        await new Promise((resolve) => {
            video.onloadedmetadata = resolve;
        });
        
        this.isScanning = true;
        this.updateStatus('Native camera active - Ready to scan!', 'success');
        
        // Start scanning with jsQR if available
        this.startNativeScanning(video, canvas);
    }
    
    startNativeScanning(video, canvas) {
        const scanFrame = () => {
            if (!this.isScanning) return;
            
            const context = canvas.getContext('2d');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            if (canvas.width > 0 && canvas.height > 0) {
                context.drawImage(video, 0, 0);
                
                // Try to use jsQR if available
                if (typeof jsQR !== 'undefined') {
                    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
                    const code = jsQR(imageData.data, imageData.width, imageData.height);
                    
                    if (code) {
                        console.log('Native QR detected:', code.data);
                        this.handleSuccess(code.data);
                        return;
                    }
                }
            }
            
            requestAnimationFrame(scanFrame);
        };
        
        scanFrame();
    }
    
    async tryFileInput() {
        this.updateStatus('Setting up file upload scanner...', 'info');
        
        const cameraArea = document.getElementById(`${this.containerId}-camera-area`);
        cameraArea.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: white; text-align: center; flex-direction: column;">
                <div style="font-size: 48px; margin-bottom: 20px;">📁</div>
                <h5>File Upload Scanner</h5>
                <p>Camera not available - Use file upload below</p>
            </div>
        `;
        
        document.getElementById('fallback-controls').style.display = 'block';
        this.updateStatus('File upload ready - Select image with QR code', 'warning');
        
        throw new Error('Camera not available - file input ready');
    }
    
    async tryManualEntry() {
        this.updateStatus('Manual entry available', 'warning');
        
        const cameraArea = document.getElementById(`${this.containerId}-camera-area`);
        cameraArea.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: white; text-align: center; flex-direction: column;">
                <div style="font-size: 48px; margin-bottom: 20px;">⌨️</div>
                <h5>Manual Entry</h5>
                <p>Enter QR code value manually below</p>
            </div>
        `;
        
        document.getElementById('fallback-controls').style.display = 'block';
    }
    
    async processFile(file) {
        this.updateStatus('Processing image...', 'info');
        
        try {
            if (typeof Html5Qrcode !== 'undefined') {
                const result = await Html5Qrcode.scanFile(file, true);
                this.handleSuccess(result);
            } else {
                throw new Error('QR library not available');
            }
        } catch (error) {
            console.error('File processing failed:', error);
            this.updateStatus('Could not read QR from image', 'error');
        }
    }
    
    async waitForLibrary() {
        return new Promise((resolve) => {
            const check = () => {
                if (typeof Html5Qrcode !== 'undefined') {
                    resolve();
                } else {
                    setTimeout(check, 100);
                }
            };
            check();
        });
    }
    
    wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    handleSuccess(qrText) {
        console.log('BulletproofQR: QR code detected:', qrText);
        this.updateStatus(`QR Code: ${qrText}`, 'success');
        
        if (this.onSuccess) {
            this.onSuccess(qrText);
        }
        
        // Reset status after 3 seconds
        setTimeout(() => {
            if (this.isScanning) {
                this.updateStatus('Ready for next scan', 'success');
            }
        }, 3000);
    }
    
    async stop() {
        this.isScanning = false;
        
        if (this.scanner && typeof this.scanner.stop === 'function') {
            try {
                await this.scanner.stop();
            } catch (error) {
                console.log('Scanner stop error:', error);
            }
        }
        
        this.updateStatus('Scanner stopped', 'info');
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
        console.log('BulletproofQR: Success callback set');
    }
}

// Export
window.BulletproofQRScanner = BulletproofQRScanner;
console.log('BulletproofQRScanner loaded - Universal QR scanning ready');