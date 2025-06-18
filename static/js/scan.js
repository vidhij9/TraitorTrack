// Wait for both DOM and QR library to load
function initializeScanner() {
    if (typeof Html5Qrcode === 'undefined') {
        console.log('QR Scanner library not loaded yet, retrying...');
        setTimeout(initializeScanner, 100);
        return;
    }
    
    const qrIdInput = document.getElementById('qr_id');
    const scanResultDiv = document.getElementById('scan-result');
    const resultQrId = document.getElementById('result-qrid');
    const startScannerBtn = document.getElementById('start-scanner');
    const stopScannerBtn = document.getElementById('stop-scanner');
    
    // Check for QR code parameter in URL
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('qr')) {
        const qrId = urlParams.get('qr');
        qrIdInput.value = qrId;
        showScanResult(qrId);
    }
    
    let html5QrCode;
    
    // Initialize scanner on button click
    startScannerBtn.addEventListener('click', startScanner);
    stopScannerBtn.addEventListener('click', stopScanner);
    
    // Auto-start scanner when page loads
    setTimeout(() => {
        startScanner();
    }, 500); // Small delay to ensure DOM is fully ready
    
    function startScanner() {
        if (typeof Html5Qrcode === 'undefined') {
            alert('QR Scanner library not loaded. Please refresh the page.');
            return;
        }
        
        // Update button states
        startScannerBtn.style.display = 'none';
        stopScannerBtn.style.display = 'inline-block';
        
        html5QrCode = new Html5Qrcode("reader");
        const config = { fps: 10, qrbox: { width: 250, height: 250 } };
        
        html5QrCode.start(
            { facingMode: "environment" }, // Use rear camera if available
            config,
            onScanSuccess,
            onScanFailure
        ).catch(function (err) {
            console.error(`Unable to start scanning: ${err}`);
            console.log("Could not access the camera: ", err);
            
            // Reset button states on error
            startScannerBtn.style.display = 'inline-block';
            stopScannerBtn.style.display = 'none';
            
            alert(`Camera error: ${err}. Please make sure you've granted camera permissions.`);
        });
    }
    
    function stopScanner() {
        if (html5QrCode && html5QrCode.isScanning) {
            html5QrCode.stop().then(() => {
                console.log('QR Code scanning stopped.');
                // Reset button states
                startScannerBtn.style.display = 'inline-block';
                stopScannerBtn.style.display = 'none';
            }).catch(err => {
                console.error('Failed to stop QR Code scanning:', err);
                // Reset button states even on error
                startScannerBtn.style.display = 'inline-block';
                stopScannerBtn.style.display = 'none';
            });
        }
    }
    
    function onScanSuccess(decodedText, decodedResult) {
        // Stop scanning after successful scan
        stopScanner();
        
        // Set the QR ID in the form and show the result
        qrIdInput.value = decodedText;
        showScanResult(decodedText);
    }
    
    function onScanFailure(error) {
        // Handle scan failure silently
        console.log(`QR scan error: ${error}`);
    }
    
    function showScanResult(qrId) {
        resultQrId.textContent = qrId;
        scanResultDiv.style.display = 'block';
        
        // Automatically check if the product exists
        fetchProductDetails(qrId);
    }
    
    function fetchProductDetails(qrId) {
        fetch(`/api/product/${qrId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show a badge indicating this is an existing product
                    const scanResultHeading = document.querySelector('#scan-result .alert-heading');
                    scanResultHeading.innerHTML = '<i class="fas fa-check-circle me-2"></i>Known Product Detected!';
                    
                    // Add product name to the result
                    const resultInfo = document.createElement('p');
                    resultInfo.innerHTML = `Product Name: <strong>${data.product.name}</strong>`;
                    
                    // Insert it after the QR ID
                    const qrIdParagraph = document.querySelector('#scan-result p');
                    qrIdParagraph.insertAdjacentElement('afterend', resultInfo);
                }
            })
            .catch(error => {
                console.error('Error fetching product details:', error);
            });
    }
    
    // Load recent scans by the current user
    fetchRecentUserScans();
    
    function fetchRecentUserScans() {
        const recentScansTable = document.getElementById('recent-user-scans');
        if (!recentScansTable) return;
        
        fetch('/api/scans?limit=10')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const tbody = recentScansTable.querySelector('tbody');
                    
                    if (data.scans.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No scans found</td></tr>';
                        return;
                    }
                    
                    tbody.innerHTML = '';
                    
                    data.scans.forEach(scan => {
                        const row = document.createElement('tr');
                        
                        const statusClass = 
                            scan.status === 'delivered' ? 'bg-success' :
                            scan.status === 'in-transit' ? 'bg-info' :
                            scan.status === 'received' ? 'bg-primary' :
                            scan.status === 'returned' ? 'bg-warning' :
                            'bg-secondary';
                        
                        row.innerHTML = `
                            <td>${scan.product_name}</td>
                            <td>${scan.product_qr}</td>
                            <td>${scan.location_name}</td>
                            <td><span class="badge ${statusClass}">${scan.status}</span></td>
                            <td>${formatDateTime(scan.timestamp)}</td>
                            <td>
                                <a href="/product/${scan.product_qr}" class="btn btn-sm btn-outline-primary">
                                    <i class="fas fa-eye"></i>
                                </a>
                            </td>
                        `;
                        
                        tbody.appendChild(row);
                    });
                } else {
                    console.error('Failed to fetch scans:', data.error);
                }
            })
            .catch(error => {
                console.error('Error fetching scans:', error);
            });
    }
    
    function formatDateTime(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleString();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initializeScanner);
