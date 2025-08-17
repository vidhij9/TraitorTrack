// Bill Parent Bag Scanner Module
class BillScanner {
    constructor(billId) {
        this.billId = billId;
        this.scanner = null;
        this.isScanning = false;
        this.lastScanTime = 0;
        this.scanCooldown = 1500;
        this.processedCodes = new Set();
    }

    async init() {
        try {
            // Check if Html5Qrcode is available
            if (typeof Html5Qrcode === 'undefined') {
                throw new Error('QR Scanner library not loaded');
            }

            this.scanner = new Html5Qrcode("qr-reader");
            console.log('Scanner initialized successfully');
            return true;
        } catch (error) {
            console.error('Scanner initialization failed:', error);
            this.showError('Scanner initialization failed: ' + error.message);
            return false;
        }
    }

    async start() {
        if (!this.scanner) {
            const initialized = await this.init();
            if (!initialized) return false;
        }

        try {
            const config = {
                fps: 10,
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0,
                rememberLastUsedCamera: true,
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true
                }
            };

            // Try back camera first
            try {
                await this.scanner.start(
                    { facingMode: "environment" },
                    config,
                    (qrCode) => this.onScanSuccess(qrCode),
                    (error) => {
                        // Ignore scan errors (happens when no QR code is in view)
                        if (!error.includes('NotFoundException')) {
                            console.warn('Scan error:', error);
                        }
                    }
                );
            } catch (err) {
                // Fallback to any available camera
                console.log('Back camera failed, trying any camera');
                const cameras = await Html5Qrcode.getCameras();
                if (cameras && cameras.length > 0) {
                    await this.scanner.start(
                        cameras[0].id,
                        config,
                        (qrCode) => this.onScanSuccess(qrCode),
                        (error) => {
                            if (!error.includes('NotFoundException')) {
                                console.warn('Scan error:', error);
                            }
                        }
                    );
                } else {
                    throw new Error('No cameras found');
                }
            }

            this.isScanning = true;
            this.showStatus('Scanner active - Position QR code in view', 'success');
            return true;
        } catch (error) {
            console.error('Failed to start scanner:', error);
            this.showError('Camera error: ' + error.message);
            return false;
        }
    }

    async stop() {
        if (this.scanner && this.isScanning) {
            try {
                await this.scanner.stop();
                this.isScanning = false;
                this.showStatus('Scanner stopped', 'secondary');
                return true;
            } catch (error) {
                console.error('Error stopping scanner:', error);
                return false;
            }
        }
        return false;
    }

    onScanSuccess(qrCode) {
        const now = Date.now();
        
        // Check cooldown
        if (now - this.lastScanTime < this.scanCooldown) {
            return;
        }

        // Check if already processed
        if (this.processedCodes.has(qrCode)) {
            return;
        }

        this.lastScanTime = now;
        this.processedCodes.add(qrCode);
        
        // Remove from processed after cooldown
        setTimeout(() => {
            this.processedCodes.delete(qrCode);
        }, this.scanCooldown);

        // Process the scan
        this.processScan(qrCode);
    }

    async processScan(qrCode) {
        try {
            const formData = new URLSearchParams();
            formData.append('bill_id', this.billId);
            formData.append('qr_code', qrCode);

            const response = await fetch('/process_bill_parent_scan', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.showToast(data.message, 'success');
                this.addBagToUI(data.bag_qr || qrCode);
                this.updateProgress();
            } else {
                // Different toast types based on error
                let toastType = 'danger';
                if (data.message.includes('already linked to this bill')) {
                    toastType = 'info';
                } else if (data.message.includes('already linked to different bill')) {
                    toastType = 'warning';
                }
                this.showToast(data.message, toastType);
            }
        } catch (error) {
            console.error('Error processing scan:', error);
            this.showToast('Network error. Please try again.', 'danger');
        }
    }

    addBagToUI(qrCode) {
        // Hide placeholder if exists
        const placeholder = document.getElementById('bags-list-placeholder');
        if (placeholder) {
            placeholder.style.display = 'none';
        }

        // Check if already in list
        if (document.querySelector(`[data-qr="${qrCode}"]`)) {
            return;
        }

        // Create new list item
        const listContainer = document.getElementById('linked-bags-list');
        const newItem = document.createElement('div');
        newItem.className = 'list-group-item d-flex justify-content-between align-items-center mb-2';
        newItem.setAttribute('data-qr', qrCode);
        
        const now = new Date();
        newItem.innerHTML = `
            <div>
                <i class="fas fa-check-circle text-success me-2"></i>
                <strong>${qrCode}</strong>
                <br>
                <small class="text-muted">Linked at ${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}</small>
            </div>
            <button class="btn btn-sm btn-outline-danger" onclick="removeBag('${qrCode}')">
                <i class="fas fa-unlink"></i>
            </button>
        `;
        
        // Insert at top of list
        listContainer.insertBefore(newItem, listContainer.firstChild);
        
        // Update count
        const bagCount = document.getElementById('bag-count');
        const currentCount = parseInt(bagCount.textContent) + 1;
        bagCount.textContent = currentCount;
    }

    updateProgress() {
        const bagCount = document.getElementById('bag-count');
        const maxCount = document.getElementById('max-count');
        const progressBar = document.getElementById('progress-bar');
        const progressPercentage = document.getElementById('progress-percentage');
        
        const current = parseInt(bagCount.textContent);
        const max = parseInt(maxCount.textContent);
        const percentage = Math.round((current / max) * 100);
        
        progressBar.style.width = percentage + '%';
        progressPercentage.textContent = percentage + '%';
        
        // Update color based on progress
        progressBar.className = 'progress-bar progress-bar-striped progress-bar-animated';
        if (percentage >= 100) {
            progressBar.classList.add('bg-success');
        } else if (percentage >= 75) {
            progressBar.classList.add('bg-info');
        } else if (percentage >= 50) {
            progressBar.classList.add('bg-warning');
        }
    }

    showStatus(message, type = 'info') {
        const resultContainer = document.getElementById('result-container');
        resultContainer.className = `alert alert-${type} mt-3`;
        resultContainer.innerHTML = `<i class="fas fa-${type === 'success' ? 'check' : 'info'}-circle me-2"></i>${message}`;
        resultContainer.style.display = 'block';
    }

    showError(message) {
        const resultContainer = document.getElementById('result-container');
        resultContainer.className = 'alert alert-danger mt-3';
        resultContainer.innerHTML = `<i class="fas fa-exclamation-circle me-2"></i>${message}`;
        resultContainer.style.display = 'block';
    }

    showToast(message, type = 'success', duration = 3000) {
        const toast = document.getElementById('scan-toast');
        const toastMessage = document.getElementById('toast-message');
        
        // Update toast style
        toast.className = `toast align-items-center border-0 bg-${type} text-white`;
        
        // Set message with icon
        let icon = 'check-circle';
        if (type === 'danger') icon = 'exclamation-circle';
        else if (type === 'warning') icon = 'exclamation-triangle';
        else if (type === 'info') icon = 'info-circle';
        
        toastMessage.innerHTML = `<i class="fas fa-${icon} me-2"></i>${message}`;
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast, { delay: duration });
        bsToast.show();
    }
}

// Export for global use
window.BillScanner = BillScanner;