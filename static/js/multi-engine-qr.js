/**
 * Multi-Engine QR Scanner Fallback
 * Uses multiple libraries and approaches for maximum compatibility
 */

class MultiEngineQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.engines = [];
        this.currentEngine = null;
        this.onSuccess = null;
        
        console.log('MultiEngine: Initializing fallback system');
        this.initializeEngines();
    }
    
    async initializeEngines() {
        // Engine 1: HTML5-QRCode (Primary)
        if (typeof Html5Qrcode !== 'undefined') {
            this.engines.push({
                name: 'HTML5-QRCode',
                start: () => this.startHtml5Engine(),
                priority: 1
            });
        }
        
        // Engine 2: Native getUserMedia + Canvas (Fallback)
        this.engines.push({
            name: 'Native Canvas',
            start: () => this.startNativeEngine(),
            priority: 2
        });
        
        // Engine 3: File Input (Last resort)
        this.engines.push({
            name: 'File Input',
            start: () => this.startFileEngine(),
            priority: 3
        });
        
        console.log(`MultiEngine: ${this.engines.length} engines available`);
        await this.tryEngines();
    }
    
    async tryEngines() {
        for (const engine of this.engines) {
            try {
                console.log(`MultiEngine: Trying ${engine.name}...`);
                await engine.start();
                this.currentEngine = engine;
                console.log(`MultiEngine: ${engine.name} started successfully`);
                return;
            } catch (error) {
                console.log(`MultiEngine: ${engine.name} failed:`, error);
            }
        }
        
        console.error('MultiEngine: All engines failed');
        this.showFailureUI();
    }
    
    async startHtml5Engine() {
        this.container.innerHTML = `
            <div id="${this.containerId}-html5" style="width: 100%; height: 400px; background: #000; border-radius: 8px;"></div>
            <div style="text-align: center; margin-top: 10px;">
                <div class="badge bg-success">HTML5 Engine Active</div>
            </div>
        `;
        
        const scanner = new Html5Qrcode(`${this.containerId}-html5`);
        const cameras = await Html5Qrcode.getCameras();
        
        if (cameras.length === 0) {
            throw new Error('No cameras found');
        }
        
        await scanner.start(
            cameras[0].id,
            { fps: 30, qrbox: 250 },
            (text) => this.handleSuccess(text),
            () => {}
        );
        
        this.scanner = scanner;
    }
    
    async startNativeEngine() {
        this.container.innerHTML = `
            <div style="position: relative;">
                <video id="${this.containerId}-video" autoplay style="width: 100%; height: 400px; background: #000; border-radius: 8px;"></video>
                <canvas id="${this.containerId}-canvas" style="display: none;"></canvas>
                <div style="text-align: center; margin-top: 10px;">
                    <div class="badge bg-warning">Native Engine Active</div>
                </div>
            </div>
        `;
        
        const video = document.getElementById(`${this.containerId}-video`);
        const canvas = document.getElementById(`${this.containerId}-canvas`);
        const context = canvas.getContext('2d');
        
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' }
        });
        
        video.srcObject = stream;
        
        // Simple QR detection using canvas
        const detectQR = () => {
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                context.drawImage(video, 0, 0);
                
                // Basic pattern detection (simplified)
                this.scanCanvasForQR(canvas);
            }
            requestAnimationFrame(detectQR);
        };
        
        video.onloadedmetadata = () => {
            detectQR();
        };
    }
    
    scanCanvasForQR(canvas) {
        // Simplified QR detection
        // In real implementation, this would use jsQR or similar
        const context = canvas.getContext('2d');
        const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
        
        // Placeholder detection logic
        // This would integrate with jsQR or other libraries
        console.log('Native: Scanning frame...');
    }
    
    startFileEngine() {
        this.container.innerHTML = `
            <div class="text-center p-4" style="background: #f8f9fa; border-radius: 8px;">
                <h5>File Upload Scanner</h5>
                <p>Upload an image containing a QR code</p>
                <input type="file" id="${this.containerId}-file" accept="image/*" class="form-control mb-3">
                <div class="badge bg-info">File Engine Active</div>
            </div>
        `;
        
        const fileInput = document.getElementById(`${this.containerId}-file`);
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.processFile(file);
            }
        });
    }
    
    async processFile(file) {
        if (typeof Html5Qrcode !== 'undefined') {
            try {
                const result = await Html5Qrcode.scanFile(file, true);
                this.handleSuccess(result);
            } catch (error) {
                console.error('File scan failed:', error);
            }
        }
    }
    
    showFailureUI() {
        this.container.innerHTML = `
            <div class="alert alert-danger text-center">
                <h5>Camera Unavailable</h5>
                <p>Unable to access camera. Please:</p>
                <ul class="list-unstyled">
                    <li>• Allow camera permissions</li>
                    <li>• Use HTTPS connection</li>
                    <li>• Try refreshing the page</li>
                </ul>
                <button class="btn btn-primary mt-2" onclick="location.reload()">
                    <i class="fas fa-refresh me-2"></i>Retry
                </button>
            </div>
        `;
    }
    
    handleSuccess(qrText) {
        console.log('MultiEngine: QR detected:', qrText);
        if (this.onSuccess) {
            this.onSuccess(qrText);
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
    
    async stop() {
        if (this.scanner && typeof this.scanner.stop === 'function') {
            await this.scanner.stop();
        }
    }
}

window.MultiEngineQRScanner = MultiEngineQRScanner;