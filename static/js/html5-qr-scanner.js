/**
 * Ultra-Fast QR Scanner using Html5Qrcode
 * Professional-grade QR detection with millisecond response times
 */

class UltraFastQRScanner {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.html5QrCode = null;
        this.isScanning = false;
        this.lastScanTime = 0;
        this.scanCooldown = 500; // 500ms cooldown to prevent duplicates
        this.onSuccess = null;
        this.scanCount = 0;
        
        this.init();
    }
    
    init() {
        this.createUI();
        this.loadHtml5QrCode();
    }
    
    createUI() {
        this.container.innerHTML = `
            <div id="reader-${this.containerId}" class="qr-reader"></div>
            <div id="status-${this.containerId}" class="scan-status">
                <div class="status-icon">
                    <i class="fas fa-camera"></i>
                </div>
                <div class="status-text">Initializing scanner...</div>
            </div>
            <div id="result-display-${this.containerId}" class="result-display" style="display: none;">
                <div class="result-icon">✓</div>
                <div class="result-text"></div>
            </div>
            
            <style>
            .qr-reader {
                width: 100%;
                max-width: 600px;
                margin: 0 auto;
                border-radius: 12px;
                overflow: hidden;
                background: #000;
            }
            
            .qr-reader video {
                width: 100% !important;
                height: auto !important;
                border-radius: 12px;
            }
            
            #reader-${this.containerId} {
                position: relative;
            }
            
            .scan-status {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                margin: 15px 0;
                padding: 12px;
                background: rgba(0, 123, 255, 0.1);
                border-radius: 8px;
                color: #007bff;
                font-weight: 500;
            }
            
            .status-icon {
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .result-display {
                margin: 15px 0;
                padding: 15px;
                background: rgba(40, 167, 69, 0.1);
                border: 2px solid #28a745;
                border-radius: 8px;
                text-align: center;
                animation: slideIn 0.3s ease;
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .result-icon {
                font-size: 32px;
                color: #28a745;
                margin-bottom: 10px;
            }
            
            .result-text {
                font-size: 14px;
                color: #333;
                word-break: break-all;
            }
            
            /* Html5QrCode specific styles */
            #reader-${this.containerId}__scan_region {
                background: transparent !important;
            }
            
            #reader-${this.containerId}__dashboard_section_swaplink {
                display: none !important;
            }
            
            #reader-${this.containerId}__dashboard_section_csr button {
                background: #007bff !important;
                border: none !important;
                padding: 10px 20px !important;
                border-radius: 6px !important;
                color: white !important;
                font-weight: 500 !important;
            }
            </style>
        `;
    }
    
    loadHtml5QrCode() {
        // Check if Html5Qrcode is already loaded
        if (typeof Html5Qrcode !== 'undefined') {
            this.initializeScanner();
            return;
        }
        
        // Load Html5Qrcode from CDN
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js';
        script.onload = () => {
            console.log('Html5Qrcode library loaded');
            this.initializeScanner();
        };
        script.onerror = () => {
            console.error('Failed to load Html5Qrcode library');
            this.updateStatus('Failed to load scanner library', 'error');
        };
        document.head.appendChild(script);
    }
    
    initializeScanner() {
        try {
            // Create Html5Qrcode instance
            this.html5QrCode = new Html5Qrcode(`reader-${this.containerId}`);
            console.log('Html5Qrcode scanner initialized');
            this.updateStatus('Scanner ready', 'ready');
        } catch (error) {
            console.error('Failed to initialize scanner:', error);
            this.updateStatus('Scanner initialization failed', 'error');
        }
    }
    
    async start() {
        if (!this.html5QrCode) {
            console.error('Scanner not initialized');
            return;
        }
        
        if (this.isScanning) {
            console.log('Scanner already running');
            return;
        }
        
        try {
            this.updateStatus('Starting camera...', 'info');
            
            // Configuration for ultra-fast scanning
            const config = {
                fps: 30, // 30 frames per second for smooth scanning
                qrbox: { width: 250, height: 250 }, // Scanning box size
                aspectRatio: 1.0,
                // Advanced experimental features for better detection
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true
                },
                rememberLastUsedCamera: true,
                showTorchButtonIfSupported: true
            };
            
            // Success callback
            const onScanSuccess = (decodedText, decodedResult) => {
                const now = Date.now();
                
                // Prevent duplicate scans
                if (now - this.lastScanTime < this.scanCooldown) {
                    return;
                }
                
                this.lastScanTime = now;
                this.scanCount++;
                
                console.log(`QR Code detected (#${this.scanCount}):`, decodedText);
                this.handleSuccess(decodedText);
            };
            
            // Error callback (silent to avoid console spam)
            const onScanError = (errorMessage) => {
                // Silently ignore scan errors (happens when no QR code is in view)
            };
            
            // Start scanning with rear camera preference
            await this.html5QrCode.start(
                { facingMode: "environment" }, // Use rear camera
                config,
                onScanSuccess,
                onScanError
            );
            
            this.isScanning = true;
            this.updateStatus('Scanning - Point at QR code', 'scanning');
            console.log('Scanner started successfully');
            
        } catch (error) {
            console.error('Failed to start scanner:', error);
            this.updateStatus('Camera access denied or unavailable', 'error');
            
            // Try to provide helpful error message
            if (error.name === 'NotAllowedError') {
                this.updateStatus('Please allow camera access and refresh', 'error');
            } else if (error.name === 'NotFoundError') {
                this.updateStatus('No camera found on this device', 'error');
            }
        }
    }
    
    handleSuccess(qrCode) {
        // Visual feedback
        this.showResult(qrCode);
        
        // Haptic feedback if available
        if (navigator.vibrate) {
            navigator.vibrate(100);
        }
        
        // Audio feedback
        this.playBeep();
        
        // Call success callback
        if (this.onSuccess) {
            this.onSuccess(qrCode);
        }
    }
    
    showResult(qrCode) {
        const resultDisplay = document.getElementById(`result-display-${this.containerId}`);
        const resultText = resultDisplay.querySelector('.result-text');
        
        resultText.textContent = `Scanned: ${qrCode}`;
        resultDisplay.style.display = 'block';
        
        // Hide after 3 seconds
        setTimeout(() => {
            resultDisplay.style.display = 'none';
        }, 3000);
    }
    
    playBeep() {
        try {
            // Create a simple beep sound
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 800; // Frequency in Hz
            oscillator.type = 'sine';
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.1);
        } catch (e) {
            // Silently fail if audio is not supported
        }
    }
    
    updateStatus(message, type = 'info') {
        const statusEl = document.getElementById(`status-${this.containerId}`);
        if (!statusEl) return;
        
        const statusText = statusEl.querySelector('.status-text');
        const statusIcon = statusEl.querySelector('.status-icon i');
        
        statusText.textContent = message;
        
        // Update icon and color based on type
        switch(type) {
            case 'ready':
                statusIcon.className = 'fas fa-check-circle';
                statusEl.style.background = 'rgba(40, 167, 69, 0.1)';
                statusEl.style.color = '#28a745';
                break;
            case 'scanning':
                statusIcon.className = 'fas fa-qrcode';
                statusEl.style.background = 'rgba(0, 123, 255, 0.1)';
                statusEl.style.color = '#007bff';
                break;
            case 'error':
                statusIcon.className = 'fas fa-exclamation-triangle';
                statusEl.style.background = 'rgba(220, 53, 69, 0.1)';
                statusEl.style.color = '#dc3545';
                break;
            default:
                statusIcon.className = 'fas fa-info-circle';
                statusEl.style.background = 'rgba(0, 123, 255, 0.1)';
                statusEl.style.color = '#007bff';
        }
    }
    
    async stop() {
        if (!this.html5QrCode || !this.isScanning) {
            return;
        }
        
        try {
            await this.html5QrCode.stop();
            this.isScanning = false;
            this.updateStatus('Scanner stopped', 'info');
            console.log('Scanner stopped');
        } catch (error) {
            console.error('Error stopping scanner:', error);
        }
    }
    
    setSuccessCallback(callback) {
        this.onSuccess = callback;
    }
    
    clear() {
        if (this.html5QrCode && this.isScanning) {
            this.stop();
        }
        if (this.html5QrCode) {
            this.html5QrCode.clear();
        }
    }
}

// Global export
window.UltraFastQRScanner = UltraFastQRScanner;