// Universal QR Scanner - Works for both parent and child bags
class QRScanner {
    constructor(options = {}) {
        this.video = document.getElementById('video');
        this.canvas = document.getElementById('canvas');
        this.canvasContext = this.canvas.getContext('2d');
        this.startCameraBtn = document.getElementById('start-camera');
        this.stopCameraBtn = document.getElementById('stop-camera');
        this.resultContainer = document.getElementById('result-container');
        
        this.scanning = false;
        this.stream = null;
        this.lastDetectedCode = null;
        
        // Configuration
        this.onQRDetected = options.onQRDetected || this.defaultQRHandler;
        this.scannerType = options.scannerType || 'parent'; // 'parent' or 'child'
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        if (this.startCameraBtn) {
            this.startCameraBtn.addEventListener('click', () => this.startCamera());
        }
        if (this.stopCameraBtn) {
            this.stopCameraBtn.addEventListener('click', () => this.stopCamera());
        }
    }
    
    async startCamera() {
        console.log('Starting camera...');
        
        if (this.resultContainer) {
            this.resultContainer.className = 'alert alert-info';
            this.resultContainer.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting camera...';
            this.resultContainer.style.display = 'block';
        }
        
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.showError('Camera not supported on this device.');
            return;
        }
        
        try {
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 640, min: 320 },
                    height: { ideal: 480, min: 240 }
                }
            };
            
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            
            this.video.srcObject = this.stream;
            this.video.setAttribute('playsinline', true);
            this.video.setAttribute('autoplay', true);
            this.video.muted = true;
            
            await new Promise((resolve, reject) => {
                this.video.onloadedmetadata = () => {
                    console.log('Video loaded successfully');
                    // Add null safety checks for video dimensions
                    if (this.video && this.video.videoWidth && this.video.videoHeight) {
                        this.canvas.width = this.video.videoWidth;
                        this.canvas.height = this.video.videoHeight;
                    } else {
                        console.warn('Video dimensions not available, using default');
                        this.canvas.width = 640;
                        this.canvas.height = 480;
                    }
                    resolve();
                };
                this.video.onerror = reject;
                this.video.play().catch(reject);
            });
            
            // Show scanning overlay
            const scannerOverlay = document.getElementById('scanner-overlay');
            if (scannerOverlay) {
                scannerOverlay.style.display = 'flex';
            }
            
            if (this.startCameraBtn) this.startCameraBtn.disabled = true;
            if (this.stopCameraBtn) this.stopCameraBtn.disabled = false;
            
            if (this.resultContainer) {
                this.resultContainer.className = 'alert alert-success';
                this.resultContainer.innerHTML = '<i class="fas fa-camera me-2"></i>Camera active - Position QR code in scanning area';
            }
            
            // Start scanning
            this.scanning = true;
            this.scanForQRCode();
            
        } catch (error) {
            console.error('Camera error:', error);
            let errorMessage = 'Camera access failed. ';
            if (error.name === 'NotAllowedError') {
                errorMessage += 'Please allow camera permission.';
            } else if (error.name === 'NotFoundError') {
                errorMessage += 'No camera found on device.';
            } else {
                errorMessage += 'Please check camera settings.';
            }
            this.showError(errorMessage);
        }
    }
    
    stopCamera() {
        this.scanning = false;
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.video) {
            this.video.srcObject = null;
        }
        if (this.canvasContext) {
            this.canvasContext.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
        
        // Hide scanning overlay
        const scannerOverlay = document.getElementById('scanner-overlay');
        if (scannerOverlay) {
            scannerOverlay.style.display = 'none';
        }
        
        if (this.startCameraBtn) this.startCameraBtn.disabled = false;
        if (this.stopCameraBtn) this.stopCameraBtn.disabled = true;
    }
    
    scanForQRCode() {
        if (!this.scanning) return;
        
        requestAnimationFrame(() => this.scanForQRCode());
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA && typeof jsQR !== 'undefined') {
            try {
                // Draw video frame to canvas
                this.canvasContext.clearRect(0, 0, this.canvas.width, this.canvas.height);
                this.canvasContext.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                
                // Draw scanning interface
                this.drawScanningInterface();
                
                // Get image data for QR detection
                const imageData = this.canvasContext.getImageData(0, 0, this.canvas.width, this.canvas.height);
                
                // Try QR detection
                const code = jsQR(imageData.data, imageData.width, imageData.height);
                
                if (code && code.data) {
                    const qrData = code.data.trim();
                    
                    // Skip very short codes
                    if (qrData.length < 3) {
                        return;
                    }
                    
                    // Visual feedback
                    this.drawDetectionHighlight(code);
                    
                    // Haptic feedback
                    if (navigator.vibrate) {
                        navigator.vibrate(25);
                    }
                    
                    // Process QR code if it's new
                    if (this.lastDetectedCode !== qrData) {
                        this.lastDetectedCode = qrData;
                        console.log('QR detected:', qrData);
                        
                        // Stop scanning temporarily
                        this.scanning = false;
                        
                        if (this.resultContainer) {
                            this.resultContainer.className = 'alert alert-success';
                            this.resultContainer.innerHTML = '<i class="fas fa-check-circle me-2"></i>Processing QR code...';
                        }
                        
                        // Call the callback
                        this.onQRDetected(qrData);
                    }
                }
            } catch (error) {
                console.error('Scanning error:', error);
            }
        }
    }
    
    drawScanningInterface() {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        const scanSize = Math.min(this.canvas.width, this.canvas.height) * 0.5;
        
        // Draw corner brackets
        const cornerLength = 30;
        const cornerThickness = 2;
        
        this.canvasContext.strokeStyle = '#00FF00';
        this.canvasContext.lineWidth = cornerThickness;
        this.canvasContext.lineCap = 'round';
        
        const x1 = centerX - scanSize/2;
        const y1 = centerY - scanSize/2;
        const x2 = centerX + scanSize/2;
        const y2 = centerY + scanSize/2;
        
        this.canvasContext.beginPath();
        // Top-left
        this.canvasContext.moveTo(x1, y1 + cornerLength);
        this.canvasContext.lineTo(x1, y1);
        this.canvasContext.lineTo(x1 + cornerLength, y1);
        // Top-right
        this.canvasContext.moveTo(x2 - cornerLength, y1);
        this.canvasContext.lineTo(x2, y1);
        this.canvasContext.lineTo(x2, y1 + cornerLength);
        // Bottom-left
        this.canvasContext.moveTo(x1, y2 - cornerLength);
        this.canvasContext.lineTo(x1, y2);
        this.canvasContext.lineTo(x1 + cornerLength, y2);
        // Bottom-right
        this.canvasContext.moveTo(x2 - cornerLength, y2);
        this.canvasContext.lineTo(x2, y2);
        this.canvasContext.lineTo(x2, y2 - cornerLength);
        this.canvasContext.stroke();
    }
    
    drawDetectionHighlight(code) {
        if (!code.location) return;
        
        this.canvasContext.strokeStyle = '#00FF00';
        this.canvasContext.lineWidth = 3;
        this.canvasContext.fillStyle = 'rgba(0, 255, 0, 0.2)';
        
        this.canvasContext.beginPath();
        this.canvasContext.moveTo(code.location.topLeftCorner.x, code.location.topLeftCorner.y);
        this.canvasContext.lineTo(code.location.topRightCorner.x, code.location.topRightCorner.y);
        this.canvasContext.lineTo(code.location.bottomRightCorner.x, code.location.bottomRightCorner.y);
        this.canvasContext.lineTo(code.location.bottomLeftCorner.x, code.location.bottomLeftCorner.y);
        this.canvasContext.closePath();
        this.canvasContext.fill();
        this.canvasContext.stroke();
    }
    
    showError(message) {
        if (this.resultContainer) {
            this.resultContainer.className = 'alert alert-danger';
            this.resultContainer.innerHTML = '<i class="fas fa-exclamation-circle me-2"></i>' + message;
        }
    }
    
    defaultQRHandler(qrData) {
        console.log('QR Code detected:', qrData);
        if (this.resultContainer) {
            this.resultContainer.className = 'alert alert-success';
            this.resultContainer.innerHTML = '<i class="fas fa-check-circle me-2"></i>QR Code: ' + qrData;
        }
    }
    
    // Public method to restart scanning
    resumeScanning() {
        if (this.stream && !this.scanning) {
            this.scanning = true;
            this.lastDetectedCode = null;
            this.scanForQRCode();
        }
    }
    
    // Auto-start camera (for child scanner)
    autoStart(delay = 500) {
        setTimeout(() => {
            this.startCamera();
        }, delay);
    }
}

// Export for use in templates
window.QRScanner = QRScanner;