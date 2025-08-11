/**
 * Live QR Scanner - Minimal, working implementation
 * Focused on live camera scanning only
 */

class LiveQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.video = null;
        this.canvas = null;
        this.context = null;
        this.scanner = null;
        this.isScanning = false;
        this.onSuccess = null;
        
        console.log('LiveQR: Starting minimal scanner');
        this.init();
    }
    
    init() {
        this.setupUI();
        this.setupElements();
        this.setupControls();
        this.startScanning();
    }
    
    setupUI() {
        this.container.innerHTML = `
            <div class="live-qr-scanner">
                <div class="camera-container">
                    <video id="${this.containerId}-video" autoplay playsinline muted></video>
                    <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
                    
                    <!-- Scanning frame -->
                    <div class="scan-overlay">
                        <div class="scan-box">
                            <div class="corner tl"></div>
                            <div class="corner tr"></div>
                            <div class="corner bl"></div>
                            <div class="corner br"></div>
                            <div class="scan-line"></div>
                        </div>
                        <div class="scan-text">Position QR code in frame</div>
                    </div>
                    
                    <!-- Simple controls -->
                    <div class="controls">
                        <button id="torch-btn" class="control-btn" title="Toggle Flash">💡</button>
                        <button id="manual-btn" class="control-btn" title="Manual Entry">⌨️</button>
                    </div>
                    
                    <!-- Success feedback -->
                    <div class="success-flash" id="success-flash"></div>
                </div>
                
                <!-- Manual entry modal -->
                <div class="manual-modal" id="manual-modal" style="display: none;">
                    <div class="modal-content">
                        <h6>Enter QR Code</h6>
                        <input type="text" id="manual-input" placeholder="Enter QR code value" class="form-control">
                        <div class="modal-buttons">
                            <button id="manual-submit" class="btn btn-primary">Submit</button>
                            <button id="manual-close" class="btn btn-secondary">Cancel</button>
                        </div>
                    </div>
                </div>
            </div>
            
            <style>
                .live-qr-scanner {
                    position: relative;
                    width: 100%;
                    height: 400px;
                    border-radius: 8px;
                    overflow: hidden;
                    background: #000;
                }
                
                .camera-container {
                    position: relative;
                    width: 100%;
                    height: 100%;
                }
                
                #${this.containerId}-video {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }
                
                .scan-overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    pointer-events: none;
                }
                
                .scan-box {
                    position: relative;
                    width: 200px;
                    height: 200px;
                    margin-bottom: 20px;
                }
                
                .corner {
                    position: absolute;
                    width: 20px;
                    height: 20px;
                    border: 2px solid #00ff00;
                }
                
                .corner.tl {
                    top: 0;
                    left: 0;
                    border-right: none;
                    border-bottom: none;
                }
                
                .corner.tr {
                    top: 0;
                    right: 0;
                    border-left: none;
                    border-bottom: none;
                }
                
                .corner.bl {
                    bottom: 0;
                    left: 0;
                    border-right: none;
                    border-top: none;
                }
                
                .corner.br {
                    bottom: 0;
                    right: 0;
                    border-left: none;
                    border-top: none;
                }
                
                .scan-line {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: linear-gradient(to right, transparent, #00ff00, transparent);
                    animation: scanning 2s ease-in-out infinite;
                }
                
                @keyframes scanning {
                    0% { top: 0; }
                    50% { top: 196px; }
                    100% { top: 0; }
                }
                
                .scan-text {
                    color: white;
                    font-size: 14px;
                    text-shadow: 0 1px 3px rgba(0,0,0,0.7);
                }
                
                .controls {
                    position: absolute;
                    bottom: 15px;
                    left: 50%;
                    transform: translateX(-50%);
                    display: flex;
                    gap: 15px;
                    pointer-events: auto;
                }
                
                .control-btn {
                    width: 45px;
                    height: 45px;
                    border-radius: 50%;
                    background: rgba(255,255,255,0.9);
                    border: none;
                    font-size: 18px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                .control-btn:hover {
                    background: white;
                    transform: scale(1.1);
                }
                
                .control-btn.active {
                    background: #ffd700;
                }
                
                .success-flash {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 255, 0, 0.3);
                    opacity: 0;
                    pointer-events: none;
                    transition: opacity 0.2s ease;
                }
                
                .success-flash.show {
                    opacity: 1;
                }
                
                .manual-modal {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.8);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 100;
                }
                
                .modal-content {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    width: 90%;
                    max-width: 300px;
                    text-align: center;
                }
                
                .modal-content h6 {
                    margin-bottom: 15px;
                }
                
                .modal-content .form-control {
                    margin-bottom: 15px;
                }
                
                .modal-buttons {
                    display: flex;
                    gap: 10px;
                }
                
                .modal-buttons .btn {
                    flex: 1;
                }
            </style>
        `;
    }
    
    setupElements() {
        this.video = document.getElementById(`${this.containerId}-video`);
        this.canvas = document.getElementById(`${this.containerId}-canvas`);
        this.context = this.canvas.getContext('2d');
    }
    
    setupControls() {
        // Torch control
        document.getElementById('torch-btn').addEventListener('click', () => {
            this.toggleTorch();
        });
        
        // Manual entry
        document.getElementById('manual-btn').addEventListener('click', () => {
            document.getElementById('manual-modal').style.display = 'flex';
            setTimeout(() => document.getElementById('manual-input').focus(), 100);
        });
        
        document.getElementById('manual-submit').addEventListener('click', () => {
            const value = document.getElementById('manual-input').value.trim();
            if (value) {
                this.handleSuccess(value);
                this.closeManualModal();
            }
        });
        
        document.getElementById('manual-close').addEventListener('click', () => {
            this.closeManualModal();
        });
        
        document.getElementById('manual-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('manual-submit').click();
            }
        });
    }
    
    async startScanning() {
        try {
            // Try Html5Qrcode first
            await this.tryHtml5Scanner();
        } catch (error) {
            console.log('LiveQR: Html5Qrcode failed, trying native camera');
            await this.tryNativeCamera();
        }
    }
    
    async tryHtml5Scanner() {
        if (typeof Html5Qrcode === 'undefined') {
            throw new Error('Html5Qrcode not available');
        }
        
        console.log('LiveQR: Starting Html5Qrcode scanner');
        this.scanner = new Html5Qrcode(`${this.containerId}-video`);
        
        const cameras = await Html5Qrcode.getCameras();
        if (cameras.length === 0) {
            throw new Error('No cameras found');
        }
        
        // Use first available camera (prefer back if available)
        let camera = cameras[0];
        for (const cam of cameras) {
            if (cam.label && cam.label.toLowerCase().includes('back')) {
                camera = cam;
                break;
            }
        }
        
        const config = {
            fps: 10,
            qrbox: { width: 200, height: 200 },
            aspectRatio: 1.0
        };
        
        await this.scanner.start(
            camera.id,
            config,
            (decodedText) => {
                console.log('LiveQR: QR detected via Html5Qrcode:', decodedText);
                this.handleSuccess(decodedText);
            },
            () => {
                // Silent error handling
            }
        );
        
        this.isScanning = true;
        console.log('LiveQR: Html5Qrcode scanner started');
    }
    
    async tryNativeCamera() {
        console.log('LiveQR: Starting native camera');
        
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment',
                width: { ideal: 640 },
                height: { ideal: 480 }
            }
        });
        
        this.video.srcObject = stream;
        
        await new Promise((resolve) => {
            this.video.onloadedmetadata = () => {
                this.video.play();
                resolve();
            };
        });
        
        this.isScanning = true;
        this.startNativeScanning();
        console.log('LiveQR: Native camera started');
    }
    
    startNativeScanning() {
        if (typeof jsQR === 'undefined') {
            console.log('LiveQR: jsQR not available for native scanning');
            return;
        }
        
        let frame = 0;
        const scan = () => {
            if (!this.isScanning) return;
            
            frame++;
            // Scan every 5th frame for performance
            if (frame % 5 === 0) {
                try {
                    this.canvas.width = this.video.videoWidth;
                    this.canvas.height = this.video.videoHeight;
                    
                    if (this.canvas.width > 0 && this.canvas.height > 0) {
                        this.context.drawImage(this.video, 0, 0);
                        const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
                        const code = jsQR(imageData.data, imageData.width, imageData.height);
                        
                        if (code) {
                            console.log('LiveQR: QR detected via jsQR:', code.data);
                            this.handleSuccess(code.data);
                            return;
                        }
                    }
                } catch (error) {
                    // Silent error handling
                }
            }
            
            requestAnimationFrame(scan);
        };
        
        scan();
    }
    
    async toggleTorch() {
        try {
            const btn = document.getElementById('torch-btn');
            const track = this.video.srcObject?.getVideoTracks()[0];
            
            if (track && track.getCapabilities && track.getCapabilities().torch) {
                const isOn = btn.classList.contains('active');
                await track.applyConstraints({
                    advanced: [{ torch: !isOn }]
                });
                btn.classList.toggle('active');
            }
        } catch (error) {
            console.log('LiveQR: Torch not supported');
        }
    }
    
    closeManualModal() {
        document.getElementById('manual-modal').style.display = 'none';
        document.getElementById('manual-input').value = '';
    }
    
    handleSuccess(qrText) {
        console.log('LiveQR: Success:', qrText);
        
        // Flash effect
        const flash = document.getElementById('success-flash');
        flash.classList.add('show');
        setTimeout(() => flash.classList.remove('show'), 200);
        
        // Haptic feedback
        if (navigator.vibrate) {
            navigator.vibrate(100);
        }
        
        if (this.onSuccess) {
            this.onSuccess(qrText);
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
    
    async stop() {
        this.isScanning = false;
        
        if (this.scanner && typeof this.scanner.stop === 'function') {
            try {
                await this.scanner.stop();
            } catch (error) {
                console.log('LiveQR: Scanner stop error:', error);
            }
        }
        
        if (this.video && this.video.srcObject) {
            const tracks = this.video.srcObject.getTracks();
            tracks.forEach(track => track.stop());
            this.video.srcObject = null;
        }
    }
}

// Export
window.LiveQRScanner = LiveQRScanner;
console.log('LiveQRScanner loaded - Minimal live scanning ready');