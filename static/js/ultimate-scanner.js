/**
 * Ultimate QR Scanner - Combines client and server processing
 * Features:
 * - Client-side fast scanning with jsQR
 * - Server-side advanced processing with OpenCV
 * - Auto-boost mode for difficult codes
 * - Manual entry fallback
 */

class UltimateScanner {
    constructor(containerId, onSuccess, scanType = 'unknown') {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.scanType = scanType; // 'parent' or 'child'
        this.scanning = false;
        this.lastScan = '';
        this.failCount = 0;
        this.useServerProcessing = false;
        this.boostMode = false;
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = `
            <div class="scanner-container" style="position:relative;width:100%;background:#000;border-radius:8px;overflow:hidden;">
                <!-- Camera View -->
                <div id="camera-view" style="position:relative;height:400px;">
                    <video id="qr-video" style="width:100%;height:100%;object-fit:cover;" muted autoplay playsinline></video>
                    <canvas id="qr-canvas" style="display:none;"></canvas>
                    <canvas id="capture-canvas" style="display:none;"></canvas>
                    
                    <!-- Scan Region -->
                    <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:220px;height:220px;">
                        <div style="width:100%;height:100%;border:3px solid #0f0;"></div>
                        <div style="position:absolute;top:-3px;left:-3px;width:25px;height:25px;border-top:4px solid #0f0;border-left:4px solid #0f0;"></div>
                        <div style="position:absolute;top:-3px;right:-3px;width:25px;height:25px;border-top:4px solid #0f0;border-right:4px solid #0f0;"></div>
                        <div style="position:absolute;bottom:-3px;left:-3px;width:25px;height:25px;border-bottom:4px solid #0f0;border-left:4px solid #0f0;"></div>
                        <div style="position:absolute;bottom:-3px;right:-3px;width:25px;height:25px;border-bottom:4px solid #0f0;border-right:4px solid #0f0;"></div>
                    </div>
                    
                    <!-- Status -->
                    <div id="scan-status" style="position:absolute;bottom:10px;left:0;right:0;text-align:center;color:#fff;font-weight:bold;background:rgba(0,0,0,0.8);padding:10px;">
                        <div id="status-text">Initializing camera...</div>
                        <div id="processing-mode" style="font-size:12px;color:#0f0;margin-top:5px;"></div>
                    </div>
                </div>
                
                <!-- Failure Options (Hidden by default) -->
                <div id="failure-options" style="display:none;padding:15px;background:#f8f9fa;border-top:2px solid #dee2e6;">
                    <div class="alert alert-warning mb-3">
                        <strong>Having trouble scanning?</strong> The QR code might be damaged or in poor lighting.
                    </div>
                    
                    <!-- Auto-Boost Button -->
                    <button id="boost-btn" class="btn btn-primary btn-lg w-100 mb-3" onclick="scanner.enableBoostMode()">
                        <i class="fas fa-rocket"></i> Try Auto-Boost Mode
                        <small class="d-block" style="font-size:12px;">Heavy processing - may take longer</small>
                    </button>
                    
                    <!-- Manual Entry Toggle -->
                    <button id="manual-toggle" class="btn btn-secondary btn-lg w-100" onclick="scanner.showManualEntry()">
                        <i class="fas fa-keyboard"></i> Enter QR Code Manually
                    </button>
                </div>
                
                <!-- Manual Entry Form (Hidden by default) -->
                <div id="manual-entry" style="display:none;padding:15px;background:#f8f9fa;">
                    <h5>Manual QR Code Entry</h5>
                    <div class="input-group">
                        <input type="text" id="manual-qr-input" class="form-control form-control-lg" 
                               placeholder="Enter QR code or batch number" maxlength="50">
                        <button class="btn btn-success" onclick="scanner.submitManualEntry()">
                            <i class="fas fa-check"></i> Submit
                        </button>
                    </div>
                    <small class="text-muted">Enter the last 5-10 digits if full code is unclear</small>
                    <button class="btn btn-link btn-sm mt-2" onclick="scanner.hideManualEntry()">
                        <i class="fas fa-camera"></i> Back to Scanner
                    </button>
                </div>
            </div>
        `;
        
        this.video = document.getElementById('qr-video');
        this.canvas = document.getElementById('qr-canvas');
        this.captureCanvas = document.getElementById('capture-canvas');
        this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
        this.captureCtx = this.captureCanvas.getContext('2d');
        this.statusText = document.getElementById('status-text');
        this.processingMode = document.getElementById('processing-mode');
        
        this.startCamera();
    }
    
    async startCamera() {
        try {
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1920 },
                    height: { ideal: 1080 },
                    frameRate: { ideal: 30 }
                }
            };
            
            const stream = await navigator.mediaDevices.getUserMedia(constraints)
                .catch(() => navigator.mediaDevices.getUserMedia({ video: true }));
            
            this.video.srcObject = stream;
            this.video.play();
            
            // Setup canvas after video loads
            setTimeout(() => {
                this.canvas.width = 800;
                this.canvas.height = 600;
                this.captureCanvas.width = 800;
                this.captureCanvas.height = 600;
                this.startScanning();
            }, 500);
            
        } catch (err) {
            console.error('Camera error:', err);
            this.updateStatus('Camera Error - Check Permissions', 'error');
            this.showFailureOptions();
        }
    }
    
    startScanning() {
        this.scanning = true;
        this.updateStatus('Scanning...', 'scanning');
        this.processingMode.textContent = 'Mode: Fast Client-Side';
        this.scanLoop();
    }
    
    async scanLoop() {
        if (!this.scanning) return;
        
        try {
            if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
                // Draw video frame
                this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
                
                // Try client-side decoding first
                if (typeof jsQR !== 'undefined' && !this.useServerProcessing) {
                    const code = jsQR(imageData.data, imageData.width, imageData.height, {
                        inversionAttempts: 'attemptBoth'
                    });
                    
                    if (code && code.data) {
                        this.handleSuccess(code.data, 'client-side');
                    } else {
                        this.failCount++;
                        
                        // After 5 failures, try server processing
                        if (this.failCount > 5 && this.failCount % 10 === 0) {
                            this.tryServerProcessing();
                        }
                        
                        // Show failure options after 15 attempts
                        if (this.failCount === 15) {
                            this.showFailureOptions();
                        }
                    }
                }
                
                // If in server processing mode
                if (this.useServerProcessing) {
                    this.tryServerProcessing();
                }
            }
        } catch (e) {
            console.error('Scan error:', e);
        }
        
        // Continue scanning
        setTimeout(() => this.scanLoop(), this.boostMode ? 500 : 200);
    }
    
    async tryServerProcessing() {
        // Capture current frame
        this.captureCtx.drawImage(this.video, 0, 0, this.captureCanvas.width, this.captureCanvas.height);
        const imageData = this.captureCanvas.toDataURL('image/jpeg', 0.9);
        
        this.processingMode.textContent = this.boostMode ? 'Mode: Auto-Boost (Maximum Processing)' : 'Mode: Server-Side Advanced';
        
        const endpoint = this.boostMode ? '/api/scanner/process-boost' : '/api/scanner/process';
        
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image: imageData,
                    type: this.scanType
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.handleSuccess(result.qr_code, result.method);
            }
        } catch (e) {
            console.error('Server processing error:', e);
        }
    }
    
    handleSuccess(qrCode, method) {
        // Prevent duplicate scans
        if (qrCode === this.lastScan) return;
        
        this.lastScan = qrCode;
        this.scanning = false;
        
        // Visual feedback
        this.updateStatus(`✓ Scanned: ${qrCode}`, 'success');
        this.processingMode.textContent = `Method: ${method}`;
        
        // Audio feedback
        try {
            const beep = new Audio('data:audio/wav;base64,UklGRl4GAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YToGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUand7blmFgU7k9n1unEiBC13yO/eizEIHWq+8+OWT');
            beep.play();
        } catch {}
        
        // Haptic feedback
        if (navigator.vibrate) navigator.vibrate(200);
        
        // Callback
        if (this.onSuccess) {
            this.onSuccess(qrCode);
        }
        
        // Resume scanning after delay
        setTimeout(() => {
            this.lastScan = '';
            this.scanning = true;
            this.failCount = 0;
        }, 2000);
    }
    
    updateStatus(text, type) {
        this.statusText.textContent = text;
        
        const colors = {
            'scanning': '#fff',
            'success': '#0f0',
            'error': '#f00',
            'warning': '#ff0'
        };
        
        this.statusText.style.color = colors[type] || '#fff';
    }
    
    showFailureOptions() {
        document.getElementById('failure-options').style.display = 'block';
    }
    
    hideFailureOptions() {
        document.getElementById('failure-options').style.display = 'none';
    }
    
    enableBoostMode() {
        this.boostMode = true;
        this.useServerProcessing = true;
        this.hideFailureOptions();
        this.updateStatus('Auto-Boost Mode Active', 'warning');
        this.processingMode.textContent = 'Applying maximum processing...';
    }
    
    showManualEntry() {
        document.getElementById('camera-view').style.display = 'none';
        document.getElementById('failure-options').style.display = 'none';
        document.getElementById('manual-entry').style.display = 'block';
        document.getElementById('manual-qr-input').focus();
    }
    
    hideManualEntry() {
        document.getElementById('camera-view').style.display = 'block';
        document.getElementById('manual-entry').style.display = 'none';
        this.failCount = 0;
    }
    
    async submitManualEntry() {
        const input = document.getElementById('manual-qr-input');
        const qrCode = input.value.trim();
        
        if (!qrCode) {
            alert('Please enter a QR code');
            return;
        }
        
        try {
            const response = await fetch('/api/scanner/manual-entry', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    qr_code: qrCode,
                    type: this.scanType
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.handleSuccess(result.qr_code, 'manual entry');
                this.hideManualEntry();
                input.value = '';
            } else {
                alert(result.message || 'Invalid QR code');
            }
        } catch (e) {
            alert('Error submitting manual entry');
        }
    }
    
    stop() {
        this.scanning = false;
        if (this.video && this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
    }
}

window.UltimateScanner = UltimateScanner;
window.scanner = null; // Global reference for inline onclick handlers