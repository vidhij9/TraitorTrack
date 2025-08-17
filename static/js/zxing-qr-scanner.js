/**
 * Professional QR Code Scanner using ZXing-js
 * The most reliable QR code detection library
 */

class ZXingQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.codeReader = null;
        this.selectedDeviceId = null;
        this.isScanning = false;
        this.lastScanTime = 0;
        this.scanCooldown = 1000; // 1 second cooldown between scans
        this.onSuccess = null;
        
        // Load ZXing library
        this.loadZXing().then(() => {
            this.init();
        });
    }
    
    async loadZXing() {
        // Load the ZXing library from CDN
        if (!window.ZXing) {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://unpkg.com/@zxing/library@latest';
                script.onload = () => {
                    console.log('ZXing library loaded successfully');
                    resolve();
                };
                script.onerror = () => {
                    console.error('Failed to load ZXing library');
                    reject(new Error('Failed to load QR scanning library'));
                };
                document.head.appendChild(script);
            });
        }
    }
    
    init() {
        this.createUI();
        // Initialize ZXing code reader
        this.codeReader = new ZXing.BrowserQRCodeReader();
        console.log('ZXing QR Code Reader initialized');
    }
    
    createUI() {
        this.container.innerHTML = `
            <div class="zxing-scanner-container">
                <video id="video-${this.containerId}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 12px;"></video>
                <div class="scanner-overlay">
                    <div class="scan-region">
                        <div class="corner top-left"></div>
                        <div class="corner top-right"></div>
                        <div class="corner bottom-left"></div>
                        <div class="corner bottom-right"></div>
                        <div class="scan-line"></div>
                    </div>
                    <div class="scan-hint">
                        <span id="hint-${this.containerId}">Align QR code within frame</span>
                    </div>
                </div>
            </div>
            
            <style>
            .zxing-scanner-container {
                position: relative;
                width: 100%;
                height: 400px;
                background: #000;
                border-radius: 12px;
                overflow: hidden;
            }
            
            .scanner-overlay {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                pointer-events: none;
            }
            
            .scan-region {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 260px;
                height: 260px;
            }
            
            .corner {
                position: absolute;
                width: 40px;
                height: 40px;
                border: 4px solid #00ff88;
            }
            
            .corner.top-left {
                top: 0;
                left: 0;
                border-right: none;
                border-bottom: none;
                border-radius: 8px 0 0 0;
            }
            
            .corner.top-right {
                top: 0;
                right: 0;
                border-left: none;
                border-bottom: none;
                border-radius: 0 8px 0 0;
            }
            
            .corner.bottom-left {
                bottom: 0;
                left: 0;
                border-right: none;
                border-top: none;
                border-radius: 0 0 0 8px;
            }
            
            .corner.bottom-right {
                bottom: 0;
                right: 0;
                border-left: none;
                border-top: none;
                border-radius: 0 0 8px 0;
            }
            
            .scan-line {
                position: absolute;
                width: 100%;
                height: 3px;
                background: linear-gradient(90deg, transparent, #00ff88, transparent);
                animation: scan-animation 2s linear infinite;
                box-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
            }
            
            @keyframes scan-animation {
                0% { top: 0; opacity: 0; }
                10% { opacity: 1; }
                90% { opacity: 1; }
                100% { top: 100%; opacity: 0; }
            }
            
            .scan-hint {
                position: absolute;
                bottom: 30px;
                left: 0;
                right: 0;
                text-align: center;
                color: white;
                font-size: 14px;
                font-weight: 500;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
                background: rgba(0, 0, 0, 0.6);
                padding: 10px;
                margin: 0 20px;
                border-radius: 20px;
            }
            
            .scan-success {
                animation: success-flash 0.5s ease;
            }
            
            @keyframes success-flash {
                0%, 100% { background: transparent; }
                50% { background: rgba(0, 255, 136, 0.2); }
            }
            </style>
        `;
        
        this.video = document.getElementById(`video-${this.containerId}`);
    }
    
    async start() {
        try {
            console.log('Starting ZXing QR Scanner...');
            
            // Get available video input devices
            const videoInputDevices = await this.codeReader.listVideoInputDevices();
            
            if (videoInputDevices.length === 0) {
                throw new Error('No camera devices found');
            }
            
            // Select the rear camera if available
            let selectedDevice = videoInputDevices[0];
            for (const device of videoInputDevices) {
                if (device.label.toLowerCase().includes('back') || 
                    device.label.toLowerCase().includes('rear') ||
                    device.label.toLowerCase().includes('environment')) {
                    selectedDevice = device;
                    break;
                }
            }
            
            this.selectedDeviceId = selectedDevice.deviceId;
            console.log(`Using camera: ${selectedDevice.label || 'Default'}`);
            
            // Update hint
            this.updateHint('Scanning for QR codes...', 'success');
            
            // Start continuous scanning
            this.isScanning = true;
            await this.startContinuousScanning();
            
        } catch (error) {
            console.error('Failed to start scanner:', error);
            this.updateHint('Camera access denied or not available', 'error');
            throw error;
        }
    }
    
    async startContinuousScanning() {
        if (!this.isScanning) return;
        
        try {
            // Use decodeFromVideoDevice for continuous scanning
            await this.codeReader.decodeFromVideoDevice(
                this.selectedDeviceId,
                this.video,
                (result, error) => {
                    if (result) {
                        // QR code detected!
                        const qrCode = result.getText();
                        console.log('QR Code detected by ZXing:', qrCode);
                        
                        // Check cooldown to prevent duplicate scans
                        const now = Date.now();
                        if (now - this.lastScanTime > this.scanCooldown) {
                            this.lastScanTime = now;
                            this.handleSuccess(qrCode);
                        }
                    }
                    
                    if (error && !(error instanceof ZXing.NotFoundException)) {
                        console.error('Decode error:', error);
                    }
                }
            );
            
            console.log('ZXing scanner started successfully');
            
        } catch (error) {
            console.error('Continuous scanning error:', error);
            this.updateHint('Scanning error. Please refresh.', 'error');
        }
    }
    
    handleSuccess(qrCode) {
        console.log('Processing QR code:', qrCode);
        
        // Visual feedback
        this.container.querySelector('.zxing-scanner-container').classList.add('scan-success');
        setTimeout(() => {
            this.container.querySelector('.zxing-scanner-container').classList.remove('scan-success');
        }, 500);
        
        // Update hint
        this.updateHint(`Detected: ${qrCode}`, 'success');
        
        // Vibrate if available
        if (navigator.vibrate) {
            navigator.vibrate(200);
        }
        
        // Call success callback
        if (this.onSuccess) {
            this.onSuccess(qrCode);
        }
        
        // Reset hint after a moment
        setTimeout(() => {
            if (this.isScanning) {
                this.updateHint('Scanning for QR codes...', 'info');
            }
        }, 2000);
    }
    
    updateHint(message, type = 'info') {
        const hint = document.getElementById(`hint-${this.containerId}`);
        if (hint) {
            hint.textContent = message;
            hint.style.color = type === 'error' ? '#ff4444' : 
                              type === 'success' ? '#00ff88' : 
                              '#ffffff';
        }
    }
    
    stop() {
        console.log('Stopping ZXing scanner...');
        this.isScanning = false;
        
        if (this.codeReader) {
            this.codeReader.reset();
        }
        
        this.updateHint('Scanner stopped', 'info');
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
}

// Global export
window.ZXingQRScanner = ZXingQRScanner;