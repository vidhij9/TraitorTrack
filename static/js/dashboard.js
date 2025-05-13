document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const refreshBtn = document.getElementById('refresh-data');
    const totalProductsEl = document.getElementById('total-products');
    const totalScansEl = document.getElementById('total-scans');
    const deliveredCountEl = document.getElementById('delivered-count');
    const inTransitCountEl = document.getElementById('in-transit-count');
    const recentScansTable = document.getElementById('recent-scans-table');
    
    // Charts
    let scanActivityChart = null;
    let statusDistributionChart = null;
    let locationStatsChart = null;
    
    // Initialize dashboard
    loadDashboardData();
    
    // Event listeners
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDashboardData);
    }
    
    // Time period filter
    document.querySelectorAll('[data-period]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            const period = e.target.getAttribute('data-period');
            loadDashboardData(period);
        });
    });
    
    // Location filter
    document.querySelectorAll('[data-filter]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            const filter = e.target.getAttribute('data-filter');
            filterLocationData(filter);
        });
    });
    
    function loadDashboardData(period = 'all') {
        // Show loading indicators
        if (totalProductsEl) totalProductsEl.textContent = 'Loading...';
        if (totalScansEl) totalScansEl.textContent = 'Loading...';
        if (deliveredCountEl) deliveredCountEl.textContent = 'Loading...';
        if (inTransitCountEl) inTransitCountEl.textContent = 'Loading...';
        
        // Fetch statistics
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateStatistics(data.statistics);
                    updateCharts(data.statistics);
                }
            })
            .catch(error => {
                console.error('Error fetching dashboard data:', error);
            });
        
        // Fetch recent scans
        fetch('/api/scans?limit=20')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateRecentScansTable(data.scans);
                }
            })
            .catch(error => {
                console.error('Error fetching recent scans:', error);
            });
    }
    
    function updateStatistics(stats) {
        if (totalProductsEl) totalProductsEl.textContent = stats.total_products.toLocaleString();
        if (totalScansEl) totalScansEl.textContent = stats.total_scans.toLocaleString();
        
        // Update status counts
        const deliveredCount = stats.status_counts['delivered'] || 0;
        const inTransitCount = stats.status_counts['in-transit'] || 0;
        
        if (deliveredCountEl) deliveredCountEl.textContent = deliveredCount.toLocaleString();
        if (inTransitCountEl) inTransitCountEl.textContent = inTransitCount.toLocaleString();
    }
    
    function updateCharts(stats) {
        updateScanActivityChart();
        updateStatusDistributionChart(stats.status_counts);
        updateLocationStatsChart(stats.location_stats);
    }
    
    function updateScanActivityChart() {
        // This would typically fetch additional time-series data
        // For now, we'll create a sample chart with random data
        const ctx = document.getElementById('scan-activity-chart');
        if (!ctx) return;
        
        const labels = [];
        const data = [];
        
        // Generate last 14 days
        for (let i = 13; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
            
            // Random data for demonstration
            data.push(Math.floor(Math.random() * 50) + 10);
        }
        
        if (scanActivityChart) {
            scanActivityChart.destroy();
        }
        
        scanActivityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Scans',
                    data: data,
                    fill: true,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
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
    
    function updateStatusDistributionChart(statusCounts) {
        const ctx = document.getElementById('status-distribution-chart');
        if (!ctx) return;
        
        const statuses = Object.keys(statusCounts || {});
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
        
        if (statusDistributionChart) {
            statusDistributionChart.destroy();
        }
        
        statusDistributionChart = new Chart(ctx, {
            type: 'doughnut',
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
                            padding: 15
                        }
                    }
                }
            }
        });
    }
    
    function updateLocationStatsChart(locationStats) {
        const ctx = document.getElementById('location-stats-chart');
        if (!ctx) return;
        
        const locations = Object.keys(locationStats || {});
        const counts = locations.map(location => locationStats[location]);
        
        if (locationStatsChart) {
            locationStatsChart.destroy();
        }
        
        locationStatsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: locations,
                datasets: [{
                    label: 'Scans',
                    data: counts,
                    backgroundColor: '#0d6efd'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
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
    
    function filterLocationData(filter) {
        console.log(`Filtering locations by: ${filter}`);
        // This would typically re-fetch data with the filter
        // For now, we'll just log the action
    }
    
    function updateRecentScansTable(scans) {
        if (!recentScansTable) return;
        
        const tbody = recentScansTable.querySelector('tbody');
        
        if (scans.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">No recent scans found</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        
        scans.forEach(scan => {
            const row = document.createElement('tr');
            
            const statusClass = 
                scan.status === 'delivered' ? 'bg-success' :
                scan.status === 'in-transit' ? 'bg-info' :
                scan.status === 'received' ? 'bg-primary' :
                scan.status === 'returned' ? 'bg-warning' :
                'bg-secondary';
            
            row.innerHTML = `
                <td>${scan.product_name || 'Unknown'}</td>
                <td>${scan.product_qr}</td>
                <td>${scan.location_name}</td>
                <td><span class="badge ${statusClass}">${scan.status}</span></td>
                <td>${scan.username}</td>
                <td>${formatDateTime(scan.timestamp)}</td>
                <td>
                    <a href="/product/${scan.product_qr}" class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-eye"></i>
                    </a>
                </td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    function formatDateTime(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleString();
    }
});
