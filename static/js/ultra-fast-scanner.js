// Ultra-Fast QR Scanner - Google Lens-like performance for agricultural packets
// Optimized for instant detection on reflective plastic packaging

class UltraFastScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = null;
        this.video = null;
        this.canvasElement = null;
        this.canvas = null;
        this.scanning = false;
        this.lastResult = null;
        this.lastResultTime = 0;
        
        // Ultra-optimized settings
        this.config = {
            fps: 30,
            qrbox: { width: 250, height: 250 },
            aspectRatio: 1.0,
            disableFlip: false,
            rememberLastUsedCamera: true,
            supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA]
        };
        
        // Initialize
        this.init();
    }
    
    async init() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) {
            console.error('Container not found');
            return;
        }
        
        // Clear container
        this.container.innerHTML = '';
        
        // Create UI
        this.createUI();
        
        // Start scanner
        await this.startScanner();
    }
    
    createUI() {
        // Create scanner container
        const scannerDiv = document.createElement('div');
        scannerDiv.id = 'qr-reader';
        scannerDiv.style.cssText = `
            width: 100%;
            height: 250px;
            position: relative;
            overflow: hidden;
            background: #000;
            border-radius: 8px;
        `;
        
        // Add loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'loading-indicator';
        loadingDiv.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 14px;
            z-index: 10;
        `;
        loadingDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Initializing scanner...';
        
        scannerDiv.appendChild(loadingDiv);
        this.container.appendChild(scannerDiv);
    }
    
    async startScanner() {
        try {
            // Use Html5Qrcode for better compatibility
            const html5QrCode = new Html5Qrcode("qr-reader");
            
            // Success callback
            const qrCodeSuccessCallback = (decodedText, decodedResult) => {
                // Prevent duplicate scans
                const now = Date.now();
                if (decodedText === this.lastResult && (now - this.lastResultTime) < 500) {
                    return;
                }
                
                this.lastResult = decodedText;
                this.lastResultTime = now;
                
                // Vibrate feedback
                if (navigator.vibrate) {
                    navigator.vibrate(100);
                }
                
                // Play sound
                this.playBeep();
                
                // Handle result
                this.handleResult(decodedText);
            };
            
            // Error callback (silent)
            const qrCodeErrorCallback = (errorMessage) => {
                // Ignore errors silently for smooth scanning
            };
            
            // Get camera config
            const config = {
                fps: 30,
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0,
                disableFlip: false,
                // Advanced experimental features for better detection
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true
                },
                formatsToSupport: [Html5QrcodeSupportedFormats.QR_CODE],
                // Video constraints for optimal performance
                videoConstraints: {
                    facingMode: "environment",
                    width: { min: 640, ideal: 1280, max: 1920 },
                    height: { min: 480, ideal: 720, max: 1080 },
                    frameRate: { ideal: 30, max: 30 },
                    focusMode: "continuous",
                    exposureMode: "continuous",
                    whiteBalanceMode: "continuous"
                }
            };
            
            // Start scanning
            await html5QrCode.start(
                { facingMode: "environment" },
                config,
                qrCodeSuccessCallback,
                qrCodeErrorCallback
            );
            
            // Remove loading indicator
            const loadingIndicator = document.getElementById('loading-indicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            
            // Auto-enable torch if available
            this.enableTorch(html5QrCode);
            
            // Store instance for cleanup
            this.scanner = html5QrCode;
            
            console.log('Ultra-fast scanner started successfully');
            
        } catch (err) {
            console.error('Failed to start scanner:', err);
            this.showError('Camera access denied or not available');
        }
    }
    
    async enableTorch(scanner) {
        try {
            // Get camera capabilities
            const track = scanner.getRunningTrackCameraCapabilities();
            if (track && track.torch) {
                // Apply torch constraint
                await scanner.applyVideoConstraints({
                    advanced: [{ torch: true }],
                    torch: true
                });
                console.log('Torch enabled for agricultural scanning');
            }
        } catch (e) {
            // Try alternative method
            try {
                const stream = scanner.getRunningTrackSettings();
                if (stream && stream.torch !== undefined) {
                    await scanner.applyVideoConstraints({
                        torch: true
                    });
                }
            } catch (e2) {
                console.log('Torch not available on this device');
            }
        }
    }
    
    playBeep() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 1000;
            gainNode.gain.value = 0.3;
            
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (e) {
            // Silent fail
        }
    }
    
    handleResult(data) {
        console.log('QR Code detected:', data);
        
        // Check if this is a parent or child bag scan
        const currentPath = window.location.pathname;
        
        if (currentPath.includes('scan_parent')) {
            // Parent bag scan
            fetch('/api/scan/parent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ qr_data: data })
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    // Success feedback
                    this.showSuccess('Parent bag scanned successfully!');
                    
                    // Redirect to child scanning
                    setTimeout(() => {
                        window.location.href = result.redirect_url;
                    }, 1000);
                } else {
                    this.showError(result.error || 'Failed to process QR code');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showError('Network error occurred');
            });
            
        } else if (currentPath.includes('scan_child')) {
            // Child bag scan
            fetch('/api/scan/child', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ qr_data: data })
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    this.showSuccess(`Child bag ${result.child_count}/30 scanned!`);
                    
                    // Update UI
                    if (window.updateChildCount) {
                        window.updateChildCount(result.child_count);
                    }
                    
                    // Check if complete
                    if (result.child_count >= 30) {
                        setTimeout(() => {
                            window.location.href = '/scan/complete';
                        }, 1000);
                    }
                } else {
                    this.showError(result.error || 'Failed to process QR code');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showError('Network error occurred');
            });
        }
    }
    
    showSuccess(message) {
        const resultDiv = document.getElementById('result-container');
        if (resultDiv) {
            resultDiv.className = 'alert alert-success p-2';
            resultDiv.innerHTML = `<i class="fas fa-check-circle me-2"></i>${message}`;
        }
    }
    
    showError(message) {
        const resultDiv = document.getElementById('result-container');
        if (resultDiv) {
            resultDiv.className = 'alert alert-danger p-2';
            resultDiv.innerHTML = `<i class="fas fa-exclamation-circle me-2"></i>${message}`;
        }
    }
    
    stop() {
        if (this.scanner) {
            this.scanner.stop().then(() => {
                console.log('Scanner stopped');
            }).catch(err => {
                console.error('Failed to stop scanner:', err);
            });
        }
    }
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on a scanning page
    if (document.getElementById('simple-scanner-container')) {
        window.ultraScanner = new UltraFastScanner('simple-scanner-container');
    }
});