document.addEventListener('DOMContentLoaded', function() {
    // Toggle between map and timeline view
    const toggleMapBtn = document.getElementById('toggle-map');
    const toggleTimelineBtn = document.getElementById('toggle-timeline');
    const productMap = document.getElementById('product-map');
    const timelineView = document.getElementById('timeline-view');
    
    if (toggleMapBtn && toggleTimelineBtn) {
        toggleMapBtn.addEventListener('click', function() {
            productMap.style.display = 'block';
            timelineView.style.display = 'none';
            toggleMapBtn.classList.add('active');
            toggleTimelineBtn.classList.remove('active');
            
            // Initialize map if it hasn't been initialized yet
            if (window.productMapInitialized !== true) {
                initializeProductMap();
            }
        });
        
        toggleTimelineBtn.addEventListener('click', function() {
            productMap.style.display = 'none';
            timelineView.style.display = 'block';
            toggleMapBtn.classList.remove('active');
            toggleTimelineBtn.classList.add('active');
        });
    }
    
    // QR code download button
    const downloadQrBtn = document.getElementById('download-qr');
    if (downloadQrBtn) {
        downloadQrBtn.addEventListener('click', function() {
            const qrCanvas = document.querySelector('#qrcode canvas');
            if (!qrCanvas) return;
            
            const image = qrCanvas.toDataURL("image/png");
            const link = document.createElement('a');
            link.download = `QR_${productData.qrId}.png`;
            link.href = image;
            link.click();
        });
    }
    
    // Initialize charts
    initializeCharts();
    
    function initializeCharts() {
        // Check if we have scan data
        if (!productData || !productData.scans || productData.scans.length === 0) {
            console.log('No scan data available for charts');
            return;
        }
        
        initializeTransitTimeChart();
        initializeStatusChart();
    }
    
    function initializeTransitTimeChart() {
        const ctx = document.getElementById('transit-time-chart');
        if (!ctx) return;
        
        // Calculate time differences between scans
        const transitTimes = [];
        const labels = [];
        
        let previousScan = null;
        
        // We're looping backward because scans are in descending order (newest first)
        for (let i = productData.scans.length - 1; i >= 0; i--) {
            const scan = productData.scans[i];
            
            if (previousScan) {
                const currentTime = new Date(scan.timestamp);
                const prevTime = new Date(previousScan.timestamp);
                
                // Calculate hours between scans
                const diffHours = (currentTime - prevTime) / (1000 * 60 * 60);
                
                transitTimes.push(diffHours);
                labels.push(`${previousScan.locationName} → ${scan.locationName}`);
            }
            
            previousScan = scan;
        }
        
        // Create the chart
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Hours',
                    data: transitTimes,
                    backgroundColor: '#0d6efd'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const hours = Math.floor(context.parsed.y);
                                const minutes = Math.round((context.parsed.y - hours) * 60);
                                return `${hours} hours, ${minutes} minutes`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Hours'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }
    
    function initializeStatusChart() {
        const ctx = document.getElementById('status-chart');
        if (!ctx) return;
        
        // Count scans by status
        const statusCounts = {};
        
        productData.scans.forEach(scan => {
            statusCounts[scan.status] = (statusCounts[scan.status] || 0) + 1;
        });
        
        const statuses = Object.keys(statusCounts);
        const counts = statuses.map(status => statusCounts[status]);
        
        // Define colors for different statuses
        const backgroundColors = statuses.map(status => {
            switch(status) {
                case 'delivered': return '#28a745';
                case 'in-transit': return '#17a2b8';
                case 'received': return '#0d6efd';
                case 'returned': return '#ffc107';
                case 'damaged': return '#dc3545';
                default: return '#6c757d';
            }
        });
        
        // Create the chart
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: statuses.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
                datasets: [{
                    data: counts,
                    backgroundColor: backgroundColors,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            usePointStyle: true,
                            padding: 10
                        }
                    }
                }
            }
        });
    }
    
    function initializeProductMap() {
        if (!productData || !productData.scans || productData.scans.length === 0) {
            console.log('No scan data available for map');
            return;
        }
        
        // Check if we have locations with coordinates
        const locationsWithCoords = productData.scans.filter(scan => 
            scan.latitude && scan.longitude
        );
        
        if (locationsWithCoords.length === 0) {
            // No coordinates available, show a message
            document.getElementById('product-map').innerHTML = 
                '<div class="alert alert-info m-3">No location coordinates available for mapping.</div>';
            return;
        }
        
        // Initialize Leaflet map
        const map = L.map('product-map');
        
        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        
        // Create markers for each location
        const markers = [];
        const points = [];
        
        // Process locations in chronological order (oldest first)
        const sortedScans = [...productData.scans].sort((a, b) => 
            new Date(a.timestamp) - new Date(b.timestamp)
        );
        
        sortedScans.forEach((scan, index) => {
            if (scan.latitude && scan.longitude) {
                const point = [scan.latitude, scan.longitude];
                points.push(point);
                
                let markerIcon;
                
                // Different icons based on scan status
                if (index === sortedScans.length - 1) {
                    // Latest scan
                    markerIcon = L.divIcon({
                        className: 'custom-div-icon',
                        html: `<div class="marker-pin bg-primary"></div>`,
                        iconSize: [30, 42],
                        iconAnchor: [15, 42]
                    });
                } else if (index === 0) {
                    // First scan
                    markerIcon = L.divIcon({
                        className: 'custom-div-icon',
                        html: `<div class="marker-pin bg-success"></div>`,
                        iconSize: [30, 42],
                        iconAnchor: [15, 42]
                    });
                } else {
                    // Intermediate scans
                    markerIcon = L.divIcon({
                        className: 'custom-div-icon',
                        html: `<div class="marker-pin bg-info"></div>`,
                        iconSize: [30, 42],
                        iconAnchor: [15, 42]
                    });
                }
                
                // Create marker with popup
                const marker = L.marker(point, { icon: markerIcon })
                    .bindPopup(`
                        <strong>${scan.locationName}</strong><br>
                        Status: ${scan.status}<br>
                        Time: ${new Date(scan.timestamp).toLocaleString()}
                    `);
                
                markers.push(marker);
                marker.addTo(map);
            }
        });
        
        // Create a polyline connecting all points
        if (points.length > 1) {
            const polyline = L.polyline(points, { color: '#0d6efd' }).addTo(map);
            
            // Fit map to all markers
            map.fitBounds(polyline.getBounds(), { padding: [30, 30] });
        } else if (points.length === 1) {
            map.setView(points[0], 13);
        }
        
        // Mark the map as initialized
        window.productMapInitialized = true;
    }
});
