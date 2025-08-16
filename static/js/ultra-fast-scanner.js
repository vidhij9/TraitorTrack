/**
 * Ultra Fast QR Scanner - Minimal, instant loading
 * Optimized for production performance
 */

(function() {
    'use strict';
    
    class UltraFastScanner {
        constructor(containerId, onSuccess) {
            this.container = document.getElementById(containerId);
            this.onSuccess = onSuccess;
            this.lastScan = 0;
            this.video = null;
            this.canvas = null;
            this.ctx = null;
            this.scanning = false;
            
            this.init();
        }
        
        init() {
            // Minimal HTML - no heavy animations
            this.container.innerHTML = `
                <div style="position:relative;width:100%;height:400px;background:#000;overflow:hidden;border-radius:8px;">
                    <video id="qr-video" style="width:100%;height:100%;object-fit:cover;" playsinline autoplay muted></video>
                    <canvas id="qr-canvas" style="display:none;"></canvas>
                    <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;pointer-events:none;">
                        <div style="width:250px;height:250px;border:2px solid #0f0;opacity:0.7;"></div>
                    </div>
                    <div id="status" style="position:absolute;bottom:10px;left:0;right:0;text-align:center;color:#fff;font-size:16px;font-weight:bold;">
                        Loading camera...
                    </div>
                </div>
            `;
            
            this.video = document.getElementById('qr-video');
            this.canvas = document.getElementById('qr-canvas');
            this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
            
            // Start immediately
            this.startCamera();
        }
        
        async startCamera() {
            try {
                // Simple constraints for fastest startup
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'environment' }
                }).catch(() => {
                    // Fallback to any camera
                    return navigator.mediaDevices.getUserMedia({ video: true });
                });
                
                this.video.srcObject = stream;
                
                // Wait for video to be ready
                this.video.onloadedmetadata = () => {
                    this.canvas.width = Math.min(640, this.video.videoWidth);
                    this.canvas.height = Math.min(480, this.video.videoHeight);
                    this.updateStatus('Point at QR code', '#0f0');
                    this.scanning = true;
                    this.scan();
                };
            } catch (err) {
                this.updateStatus('Camera error - use manual entry', '#f00');
                console.error('Camera error:', err);
            }
        }
        
        scan() {
            if (!this.scanning) return;
            
            // Only scan if video is ready
            if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
                // Draw and scan at lower resolution for speed
                this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
                
                // Use jsQR if available
                if (typeof jsQR !== 'undefined') {
                    const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
                    const code = jsQR(imageData.data, imageData.width, imageData.height);
                    
                    if (code && code.data) {
                        const now = Date.now();
                        if (now - this.lastScan > 1000) {
                            this.lastScan = now;
                            this.handleSuccess(code.data);
                        }
                    }
                }
            }
            
            // Scan at 10fps for balance between speed and CPU
            setTimeout(() => this.scan(), 100);
        }
        
        handleSuccess(data) {
            // Visual feedback
            this.updateStatus('SCANNED!', '#0f0');
            
            // Simple beep
            try {
                const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBi+Gyffo');
                audio.volume = 0.3;
                audio.play();
            } catch(e) {}
            
            // Vibrate
            if (navigator.vibrate) navigator.vibrate(200);
            
            // Call handler
            if (this.onSuccess) this.onSuccess(data);
            
            // Reset status after delay
            setTimeout(() => this.updateStatus('Point at QR code', '#0f0'), 1000);
        }
        
        updateStatus(text, color) {
            const status = document.getElementById('status');
            if (status) {
                status.textContent = text;
                status.style.color = color;
            }
        }
        
        stop() {
            this.scanning = false;
            if (this.video && this.video.srcObject) {
                this.video.srcObject.getTracks().forEach(track => track.stop());
            }
        }
    }
    
    // Make globally available
    window.UltraFastScanner = UltraFastScanner;
})();