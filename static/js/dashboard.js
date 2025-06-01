// Dashboard JavaScript for TraceTrack
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const totalParentBagsEl = document.getElementById('total-parent-bags');
    const totalChildBagsEl = document.getElementById('total-child-bags');
    const totalScansEl = document.getElementById('total-scans');
    const totalBillsEl = document.getElementById('total-bills');
    const recentScansTable = document.getElementById('recent-scans-table');
    
    // Charts
    let scanActivityChart = null;
    
    // Initialize dashboard
    loadDashboardData();
    
    function loadDashboardData() {
        // Load statistics
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateStatistics(data.statistics);
                    updateCharts();
                }
            })
            .catch(error => {
                console.error('Error loading dashboard data:', error);
            });
        
        // Load recent scans
        fetch('/api/scans?limit=10')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateRecentScansTable(data.scans);
                }
            })
            .catch(error => {
                console.error('Error loading recent scans:', error);
            });
    }
    
    function updateStatistics(stats) {
        if (totalParentBagsEl) totalParentBagsEl.textContent = stats.total_parent_bags.toLocaleString();
        if (totalChildBagsEl) totalChildBagsEl.textContent = stats.total_child_bags.toLocaleString();
        if (totalScansEl) totalScansEl.textContent = stats.total_scans.toLocaleString();
        if (totalBillsEl) totalBillsEl.textContent = stats.total_bills.toLocaleString();
    }
    
    function updateCharts() {
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
            });
    }
    
    function updateRecentScansTable(scans) {
        if (!recentScansTable) return;
        
        const tbody = recentScansTable.querySelector('tbody');
        
        if (scans.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">No recent scans found</td></tr>';
            return;
        }
        
        tbody.innerHTML = '';
        
        scans.forEach(scan => {
            const row = document.createElement('tr');
            
            const typeClass = scan.type === 'parent' ? 'bg-primary' : 'bg-info';
            const typeText = scan.type === 'parent' ? 'Parent' : 'Child';
            
            row.innerHTML = `
                <td>${scan.product_qr}</td>
                <td><span class="badge ${typeClass}">${typeText}</span></td>
                <td>${scan.username}</td>
                <td>${formatDateTime(scan.timestamp)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="viewScanDetails('${scan.id}')">
                        <i class="fas fa-eye"></i>
                    </button>
                </td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    function formatDateTime(dateStr) {
        if (!dateStr) return 'N/A';
        
        const date = new Date(dateStr);
        return date.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    // Global functions
    window.viewScanDetails = function(scanId) {
        // Navigate to scan details page
        window.location.href = `/scan/${scanId}`;
    };
    
    window.refreshDashboard = function() {
        loadDashboardData();
    };
    
    // Auto-refresh every 30 seconds
    setInterval(loadDashboardData, 30000);
});