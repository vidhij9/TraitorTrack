/**
 * Simple Fast QR Scanner - Optimized for Speed and Simplicity
 * No buttons, no complexity - just point and scan
 * Designed for workers who need efficiency, not features
 */

class SimpleFastScanner {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.onSuccess = options.onSuccess || null;
        this.isScanning = false;
        this.lastScanTime = 0;
        this.video = null;
        this.canvasElement = null;
        this.canvas = null;
        
        // Initialize immediately - no waiting
        this.init();
    }
    
    init() {
        // Create simple UI
        this.container.innerHTML = `
            <div style="position: relative; width: 100%; height: 450px; background: #000; border-radius: 8px; overflow: hidden;">
                <video id="qr-video" style="width: 100%; height: 100%; object-fit: cover;"></video>
                <canvas id="qr-canvas" style="display: none;"></canvas>
                
                <!-- Big visual scanning indicator -->
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 300px; height: 300px; pointer-events: none;">
                    <!-- Animated scanning frame -->
                    <div style="position: absolute; width: 100%; height: 100%; border: 3px solid #00ff00; border-radius: 20px; animation: pulse 1.5s infinite;">
                        <!-- Corner markers -->
                        <div style="position: absolute; top: -3px; left: -3px; width: 50px; height: 50px; border-top: 5px solid #00ff00; border-left: 5px solid #00ff00;"></div>
                        <div style="position: absolute; top: -3px; right: -3px; width: 50px; height: 50px; border-top: 5px solid #00ff00; border-right: 5px solid #00ff00;"></div>
                        <div style="position: absolute; bottom: -3px; left: -3px; width: 50px; height: 50px; border-bottom: 5px solid #00ff00; border-left: 5px solid #00ff00;"></div>
                        <div style="position: absolute; bottom: -3px; right: -3px; width: 50px; height: 50px; border-bottom: 5px solid #00ff00; border-right: 5px solid #00ff00;"></div>
                    </div>
                    
                    <!-- Scanning line animation -->
                    <div style="position: absolute; top: 0; left: 0; width: 100%; height: 3px; background: linear-gradient(90deg, transparent, #00ff00, transparent); animation: scan 2s linear infinite;"></div>
                </div>
                
                <!-- Large status text for workers -->
                <div id="scanner-status" style="position: absolute; bottom: 20px; left: 0; right: 0; text-align: center; color: white; font-size: 24px; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.8); padding: 10px; background: rgba(0,0,0,0.5);">
                    📷 POINT AT QR CODE
                </div>
            </div>
            
            <style>
                @keyframes pulse {
                    0%, 100% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.7; transform: scale(1.02); }
                }
                
                @keyframes scan {
                    0% { transform: translateY(0); }
                    100% { transform: translateY(300px); }
                }
            </style>
        `;
        
        this.video = document.getElementById('qr-video');
        this.canvasElement = document.getElementById('qr-canvas');
        this.canvas = this.canvasElement.getContext('2d');
        
        // Start camera immediately
        this.startCamera();
    }
    
    async startCamera() {
        try {
            // Check if we're on HTTPS (required for camera)
            if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
                console.warn('Camera requires HTTPS. Trying anyway...');
            }
            
            // Request camera with multiple fallback options
            let stream = null;
            const constraints = [
                { video: { facingMode: 'environment' } },  // Back camera first
                { video: { facingMode: 'user' } },          // Front camera fallback
                { video: true }                             // Any camera
            ];
            
            for (const constraint of constraints) {
                try {
                    stream = await navigator.mediaDevices.getUserMedia(constraint);
                    if (stream) break;
                } catch (e) {
                    console.log('Trying next camera constraint...');
                }
            }
            
            if (!stream) {
                throw new Error('No camera available');
            }
            
            this.video.srcObject = stream;
            this.video.setAttribute('playsinline', true);
            this.video.setAttribute('autoplay', true);
            this.video.muted = true;
            
            // Wait for video to be ready
            await this.video.play();
            
            // Start scanning as soon as video is ready
            this.video.addEventListener('loadedmetadata', () => {
                this.canvasElement.width = this.video.videoWidth;
                this.canvasElement.height = this.video.videoHeight;
                this.updateStatus('📷 SCANNING...', '#00ff00');
                this.startScanning();
            });
            
        } catch (err) {
            console.error('Camera error:', err);
            this.updateStatus('❌ CAMERA ERROR', '#ff0000');
            
            // Show detailed error message
            const errorMsg = document.createElement('div');
            errorMsg.style.cssText = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; text-align: center; padding: 20px; background: rgba(255,0,0,0.8); border-radius: 10px; max-width: 80%;';
            errorMsg.innerHTML = `
                <h3>Camera Not Available</h3>
                <p>Please check:</p>
                <ul style="text-align: left;">
                    <li>Camera permissions are allowed</li>
                    <li>No other app is using camera</li>
                    <li>You're using HTTPS connection</li>
                </ul>
                <p>Use manual entry below</p>
            `;
            this.container.querySelector('div').appendChild(errorMsg);
        }
    }
    
    startScanning() {
        if (this.isScanning) return;
        this.isScanning = true;
        this.scan();
    }
    
    scan() {
        if (!this.isScanning) return;
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            // Draw current frame
            this.canvas.drawImage(this.video, 0, 0, this.canvasElement.width, this.canvasElement.height);
            
            // Get image data
            const imageData = this.canvas.getImageData(0, 0, this.canvasElement.width, this.canvasElement.height);
            
            // Try to scan with jsQR (fastest library)
            if (typeof jsQR !== 'undefined') {
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: 'attemptBoth'  // Try both normal and inverted
                });
                
                if (code && code.data) {
                    this.handleSuccess(code.data);
                }
            }
            
            // Skip Html5QrCode blob conversion - too slow
        }
        
        // Scan at 15fps for better performance
        setTimeout(() => this.scan(), 66);
    }
    
    handleSuccess(qrCode) {
        // Prevent duplicate scans
        const now = Date.now();
        if (now - this.lastScanTime < 1000) return;
        this.lastScanTime = now;
        
        // Visual feedback
        this.updateStatus('✅ SCANNED!', '#00ff00');
        
        // Make the whole screen flash green briefly
        this.container.style.background = '#00ff00';
        setTimeout(() => {
            this.container.style.background = '';
            this.updateStatus('📷 POINT AT QR CODE', '#ffffff');
        }, 500);
        
        // Audio beep
        this.playBeep();
        
        // Vibrate if supported
        if (navigator.vibrate) {
            navigator.vibrate(200);
        }
        
        // Call success handler
        if (this.onSuccess) {
            this.onSuccess(qrCode);
        }
    }
    
    updateStatus(text, color = '#ffffff') {
        const statusEl = document.getElementById('scanner-status');
        if (statusEl) {
            statusEl.textContent = text;
            statusEl.style.color = color;
        }
    }
    
    playBeep() {
        try {
            // Simple beep sound
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 1000;
            oscillator.type = 'square';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (e) {
            // No audio support
        }
    }
    
    stop() {
        this.isScanning = false;
        if (this.video && this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
    }
    
    // Check camera availability
    static async isCameraAvailable() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            return devices.some(device => device.kind === 'videoinput');
        } catch (e) {
            return false;
        }
    }
}

// Make globally available
window.SimpleFastScanner = SimpleFastScanner;