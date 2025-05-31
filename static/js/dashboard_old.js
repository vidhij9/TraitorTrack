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
    // Removed status distribution chart
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
        // Update dashboard counters with correct element IDs
        const parentBagsEl = document.getElementById('total-parent-bags');
        const childBagsEl = document.getElementById('total-child-bags');
        const billsEl = document.getElementById('total-bills');
        const scansEl = document.getElementById('total-scans');
        
        if (parentBagsEl) parentBagsEl.textContent = (stats.total_parent_bags || 0).toLocaleString();
        if (childBagsEl) childBagsEl.textContent = (stats.total_child_bags || 0).toLocaleString();
        if (billsEl) billsEl.textContent = (stats.total_bills || 0).toLocaleString();
        if (scansEl) scansEl.textContent = (stats.total_scans || 0).toLocaleString();
        
        // Legacy element updates for compatibility
        if (totalProductsEl) totalProductsEl.textContent = (stats.total_products || 0).toLocaleString();
        if (totalScansEl) totalScansEl.textContent = (stats.total_scans || 0).toLocaleString();
        
        // Update status counts
        const deliveredCount = stats.status_counts['delivered'] || 0;
        const inTransitCount = stats.status_counts['in-transit'] || 0;
        
        if (deliveredCountEl) deliveredCountEl.textContent = deliveredCount.toLocaleString();
        if (inTransitCountEl) inTransitCountEl.textContent = inTransitCount.toLocaleString();
    }
    
    function updateCharts(stats) {
        updateScanActivityChart();
    }
    
    function updateScanActivityChart() {
        const ctx = document.getElementById('scan-activity-chart');
        if (!ctx) return;
        
        // Fetch real scan activity data
        fetch('/api/activity/14')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const labels = [];
                    const scanCounts = [];
                    
                    // Generate last 14 days and get actual scan counts
                    for (let i = 13; i >= 0; i--) {
                        const date = new Date();
                        date.setDate(date.getDate() - i);
                        const dateStr = date.toISOString().split('T')[0];
                        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
                        
                        // Get actual scan count for this date
                        const dayData = data.activity.find(d => d.date === dateStr);
                        scanCounts.push(dayData ? dayData.scan_count : 0);
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
                                data: scanCounts,
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
            })
            .catch(error => {
                console.error('Error fetching scan activity data:', error);
                // Fall back to showing empty chart
                if (scanActivityChart) {
                    scanActivityChart.destroy();
                }
                
                const labels = [];
                const data = [];
                for (let i = 13; i >= 0; i--) {
                    const date = new Date();
                    date.setDate(date.getDate() - i);
                    labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
                    data.push(0);
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
    

    

    
    function updateRecentScansTable(scans) {
        if (!recentScansTable) return;
        
        const tbody = recentScansTable.querySelector('tbody');
        
        if (scans.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No recent scans found</td></tr>';
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
