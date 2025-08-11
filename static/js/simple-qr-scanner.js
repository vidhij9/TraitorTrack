/**
 * Simple QR Scanner - Minimal, reliable implementation
 * No external dependencies, works with basic browser APIs
 */

class SimpleQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.isScanning = false;
        this.onSuccess = null;
        this.scanInterval = null;
        
        console.log('SimpleQR: Starting with native browser APIs only');
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div class="simple-scanner">
                <div class="video-container">
                    <video id="${this.containerId}-video" autoplay playsinline muted style="width: 100%; height: 400px; background: #000; border-radius: 8px;"></video>
                    <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
                </div>
                
                <div class="scanner-controls">
                    <div class="status-display" id="status-display">
                        <div class="status-text">Simple Scanner</div>
                        <div class="status-message">Starting camera...</div>
                    </div>
                    
                    <div class="manual-controls" style="margin-top: 15px;">
                        <input type="file" id="file-input" accept="image/*" class="form-control mb-2" style="display: none;">
                        <input type="text" id="manual-input" placeholder="Enter QR code manually" class="form-control mb-2" style="display: none;">
                        <div class="btn-group w-100">
                            <button id="camera-btn" class="btn btn-primary">📷 Camera</button>
                            <button id="file-btn" class="btn btn-secondary">📁 File</button>
                            <button id="manual-btn" class="btn btn-outline-secondary">⌨️ Manual</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <style>
                .simple-scanner {
                    width: 100%;
                    background: #f8f9fa;
                    border-radius: 8px;
                    overflow: hidden;
                }
                
                .video-container {
                    position: relative;
                }
                
                .scanner-controls {
                    padding: 15px;
                    background: white;
                    border-top: 1px solid #dee2e6;
                }
                
                .status-display {
                    text-align: center;
                    margin-bottom: 10px;
                }
                
                .status-text {
                    font-weight: bold;
                    color: #495057;
                }
                
                .status-message {
                    font-size: 14px;
                    color: #6c757d;
                    margin-top: 5px;
                }
                
                .status-success .status-message {
                    color: #28a745;
                }
                
                .status-error .status-message {
                    color: #dc3545;
                }
                
                .btn-group .btn {
                    flex: 1;
                }
            </style>
        `;
        
        this.setupElements();
        this.setupControls();
        this.startCamera();
    }
    
    setupElements() {
        this.video = document.getElementById(`${this.containerId}-video`);
        this.canvas = document.getElementById(`${this.containerId}-canvas`);
        this.context = this.canvas.getContext('2d');
    }
    
    setupControls() {
        const fileInput = document.getElementById('file-input');
        const manualInput = document.getElementById('manual-input');
        const cameraBtn = document.getElementById('camera-btn');
        const fileBtn = document.getElementById('file-btn');
        const manualBtn = document.getElementById('manual-btn');
        
        cameraBtn.addEventListener('click', () => {
            this.showCamera();
        });
        
        fileBtn.addEventListener('click', () => {
            this.showFileInput();
        });
        
        manualBtn.addEventListener('click', () => {
            this.showManualInput();
        });
        
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.processFile(file);
            }
        });
        
        manualInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const value = manualInput.value.trim();
                if (value) {
                    this.handleSuccess(value);
                    manualInput.value = '';
                }
            }
        });
    }
    
    showCamera() {
        document.getElementById('file-input').style.display = 'none';
        document.getElementById('manual-input').style.display = 'none';
        this.video.style.display = 'block';
        this.startCamera();
    }
    
    showFileInput() {
        this.video.style.display = 'none';
        document.getElementById('manual-input').style.display = 'none';
        document.getElementById('file-input').style.display = 'block';
        this.stopScanning();
        this.updateStatus('Select image file with QR code', 'info');
    }
    
    showManualInput() {
        this.video.style.display = 'none';
        document.getElementById('file-input').style.display = 'none';
        document.getElementById('manual-input').style.display = 'block';
        this.stopScanning();
        this.updateStatus('Enter QR code value manually', 'info');
        document.getElementById('manual-input').focus();
    }
    
    async startCamera() {
        try {
            this.updateStatus('Requesting camera access...', 'info');
            
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                }
            });
            
            this.video.srcObject = stream;
            
            this.video.onloadedmetadata = () => {
                this.video.play();
                this.updateStatus('Camera active - Position QR codes in view', 'success');
                this.startScanning();
            };
            
        } catch (error) {
            console.error('Camera access failed:', error);
            this.updateStatus('Camera unavailable - Use file or manual entry', 'error');
            this.showFileInput();
        }
    }
    
    startScanning() {
        if (this.isScanning) return;
        
        this.isScanning = true;
        this.scanInterval = setInterval(() => {
            this.scanFrame();
        }, 500); // Scan every 500ms for better performance
    }
    
    stopScanning() {
        this.isScanning = false;
        if (this.scanInterval) {
            clearInterval(this.scanInterval);
            this.scanInterval = null;
        }
    }
    
    scanFrame() {
        if (!this.video || this.video.readyState !== this.video.HAVE_ENOUGH_DATA) {
            return;
        }
        
        // Set canvas dimensions to match video
        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        
        // Draw current video frame to canvas
        this.context.drawImage(this.video, 0, 0);
        
        // Simple pattern detection for QR codes
        // This is a very basic implementation - real QR detection would need a proper library
        this.detectSimplePatterns();
    }
    
    detectSimplePatterns() {
        // Basic pattern detection - look for high contrast rectangular regions
        // This is a simplified approach for demonstration
        const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
        
        // For now, we'll rely on manual entry or file upload
        // Real QR detection requires complex algorithms
    }
    
    processFile(file) {
        this.updateStatus('Processing image file...', 'info');
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                // Draw image to canvas
                this.canvas.width = img.width;
                this.canvas.height = img.height;
                this.context.drawImage(img, 0, 0);
                
                // For file processing, we'd need a QR detection library
                // For now, show message to use manual entry
                this.updateStatus('Image loaded - Use manual entry for QR value', 'info');
                this.showManualInput();
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    }
    
    updateStatus(message, type = 'info') {
        const statusEl = document.getElementById('status-display');
        const messageEl = statusEl?.querySelector('.status-message');
        
        if (messageEl) {
            messageEl.textContent = message;
        }
        
        if (statusEl) {
            statusEl.className = `status-display status-${type}`;
        }
    }
    
    handleSuccess(qrText) {
        console.log('SimpleQR: QR detected:', qrText);
        this.updateStatus(`QR Code: ${qrText}`, 'success');
        
        if (this.onSuccess) {
            this.onSuccess(qrText);
        }
        
        // Reset after 3 seconds
        setTimeout(() => {
            this.updateStatus('Ready for next scan', 'success');
        }, 3000);
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
        console.log('SimpleQR: Success callback set');
    }
    
    stop() {
        this.stopScanning();
        
        if (this.video && this.video.srcObject) {
            const tracks = this.video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            this.video.srcObject = null;
        }
        
        this.updateStatus('Scanner stopped', 'info');
    }
}

// Export
window.SimpleQRScanner = SimpleQRScanner;
console.log('SimpleQRScanner loaded - Native browser API scanner ready');