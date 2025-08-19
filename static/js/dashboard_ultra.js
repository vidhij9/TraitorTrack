/**
 * Ultra-Fast Dashboard JavaScript
 * Optimized for 40+ lakh bags and 1000+ concurrent users
 */

(function() {
    'use strict';
    
    // Configuration
    const API_CONFIG = {
        statsEndpoint: '/api/stats',
        fallbackStatsEndpoint: '/api/stats',
        scansEndpoint: '/api/scans',
        refreshInterval: 30000, // 30 seconds
        requestTimeout: 5000,   // 5 seconds timeout
        retryAttempts: 2,
        retryDelay: 1000
    };
    
    // Cache for dashboard data
    let dataCache = {
        stats: null,
        scans: null,
        lastUpdate: 0
    };
    
    // Request queue to prevent simultaneous requests
    const requestQueue = new Map();
    
    /**
     * Make API request with caching and retry logic
     */
    async function fetchWithRetry(url, options = {}, retries = API_CONFIG.retryAttempts) {
        // Check if request is already in progress
        if (requestQueue.has(url)) {
            return requestQueue.get(url);
        }
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.requestTimeout);
        
        const fetchPromise = fetch(url, {
            ...options,
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            clearTimeout(timeoutId);
            if (retries > 0 && error.name !== 'AbortError') {
                return new Promise(resolve => {
                    setTimeout(() => {
                        resolve(fetchWithRetry(url, options, retries - 1));
                    }, API_CONFIG.retryDelay);
                });
            }
            throw error;
        })
        .finally(() => {
            requestQueue.delete(url);
        });
        
        requestQueue.set(url, fetchPromise);
        return fetchPromise;
    }
    
    /**
     * Update dashboard statistics
     */
    async function updateStats() {
        try {
            // Fetch stats from API
            let data = await fetchWithRetry(API_CONFIG.statsEndpoint);
            
            // Cache the data
            dataCache.stats = data;
            dataCache.lastUpdate = Date.now();
            
            // Update UI with stats data
            updateElementSafely('total-parent-bags', data.parent_bags || 0);
            updateElementSafely('total-child-bags', data.child_bags || 0);
            updateElementSafely('total-bills', data.active_bills || 0);
            updateElementSafely('total-scans', data.recent_scans || 0);
            
            // Show success indicator
            showStatusIndicator('success');
            
        } catch (error) {
            console.error('Failed to update stats:', error);
            showStatusIndicator('error');
            
            // Use cached data if available
            if (dataCache.stats && (Date.now() - dataCache.lastUpdate) < 300000) {
                console.log('Using cached stats data');
                return;
            }
        }
    }
    
    /**
     * Update recent scans table
     */
    async function updateRecentScans() {
        try {
            const data = await fetchWithRetry(API_CONFIG.scansEndpoint + '?limit=10');
            
            if (!data.success || !data.scans) {
                throw new Error('Invalid scan data');
            }
            
            // Cache the data
            dataCache.scans = data.scans;
            
            const tbody = document.querySelector('#recent-scans-table tbody');
            if (!tbody) return;
            
            // Build HTML efficiently
            const rows = data.scans.map(scan => {
                const time = scan.timestamp ? formatTimeAgo(new Date(scan.timestamp)) : 'Unknown';
                const qrId = escapeHtml(scan.product_qr || 'Unknown');
                const type = scan.type === 'parent' ? 
                    '<span class="badge bg-primary">Parent</span>' : 
                    '<span class="badge bg-success">Child</span>';
                const username = escapeHtml(scan.username || 'Unknown');
                
                return `
                    <tr>
                        <td class="text-truncate" style="max-width: 100px;" title="${qrId}">${qrId}</td>
                        <td>${type}</td>
                        <td class="text-truncate" style="max-width: 80px;">${username}</td>
                        <td>${time}</td>
                    </tr>
                `;
            }).join('');
            
            tbody.innerHTML = rows || '<tr><td colspan="4" class="text-center">No recent scans</td></tr>';
            
        } catch (error) {
            console.error('Failed to update recent scans:', error);
            
            // Use cached data if available
            if (dataCache.scans) {
                console.log('Using cached scan data');
                return;
            }
            
            const tbody = document.querySelector('#recent-scans-table tbody');
            if (tbody) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Failed to load scans</td></tr>';
            }
        }
    }
    
    /**
     * Update recent activity from ultra-fast endpoint
     */
    function updateRecentActivity(activities) {
        const tbody = document.querySelector('#recent-scans-table tbody');
        if (!tbody || !activities || activities.length === 0) return;
        
        const rows = activities.slice(0, 10).map(activity => {
            const time = activity.timestamp ? formatTimeAgo(new Date(activity.timestamp)) : 'Unknown';
            const qrId = escapeHtml(activity.qr_id || 'Unknown');
            const type = activity.scan_type === 'parent' ? 
                '<span class="badge bg-primary">Parent</span>' : 
                '<span class="badge bg-success">Child</span>';
            const username = escapeHtml(activity.username || 'Unknown');
            
            return `
                <tr>
                    <td class="text-truncate" style="max-width: 100px;" title="${qrId}">${qrId}</td>
                    <td>${type}</td>
                    <td class="text-truncate" style="max-width: 80px;">${username}</td>
                    <td>${time}</td>
                </tr>
            `;
        }).join('');
        
        tbody.innerHTML = rows;
    }
    
    /**
     * Safely update element text content
     */
    function updateElementSafely(id, value) {
        const element = document.getElementById(id);
        if (element) {
            // Animate number changes
            const currentValue = parseInt(element.textContent) || 0;
            const targetValue = parseInt(value) || 0;
            
            if (currentValue !== targetValue) {
                animateNumber(element, currentValue, targetValue, 500);
            }
        }
    }
    
    /**
     * Animate number changes
     */
    function animateNumber(element, start, end, duration) {
        const range = end - start;
        const startTime = performance.now();
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const value = Math.floor(start + range * progress);
            element.textContent = value.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        
        requestAnimationFrame(update);
    }
    
    /**
     * Format time ago
     */
    function formatTimeAgo(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        
        if (seconds < 60) return 'just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
        
        return date.toLocaleDateString();
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Show status indicator
     */
    function showStatusIndicator(status) {
        const refreshBtn = document.getElementById('refresh-data');
        if (!refreshBtn) return;
        
        const icon = refreshBtn.querySelector('i');
        if (!icon) return;
        
        icon.className = status === 'success' ? 
            'fas fa-check text-success' : 
            'fas fa-exclamation-triangle text-warning';
        
        setTimeout(() => {
            icon.className = 'fas fa-sync-alt';
        }, 2000);
    }
    
    /**
     * View scan details
     */
    window.viewScanDetails = function(qrId) {
        // Navigate to scan details page
        window.location.href = `/scan/details?qr=${encodeURIComponent(qrId)}`;
    };
    
    /**
     * Initialize dashboard
     */
    function initDashboard() {
        // Initial load
        Promise.all([
            updateStats(),
            updateRecentScans()
        ]).catch(error => {
            console.error('Dashboard initialization error:', error);
        });
        
        // Set up refresh button
        const refreshBtn = document.getElementById('refresh-data');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                const icon = this.querySelector('i');
                if (icon) {
                    icon.classList.add('fa-spin');
                }
                
                Promise.all([
                    updateStats(),
                    updateRecentScans()
                ]).finally(() => {
                    if (icon) {
                        icon.classList.remove('fa-spin');
                    }
                });
            });
        }
        
        // Auto-refresh
        setInterval(() => {
            updateStats();
            updateRecentScans();
        }, API_CONFIG.refreshInterval);
        
        // Visibility change handler - refresh when tab becomes active
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden && (Date.now() - dataCache.lastUpdate) > 60000) {
                updateStats();
                updateRecentScans();
            }
        });
    }
    
    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDashboard);
    } else {
        initDashboard();
    }
    
})();