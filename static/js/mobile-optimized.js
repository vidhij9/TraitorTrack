/**
 * Mobile-Optimized JavaScript for TraceTrack
 * Enhanced performance and touch interactions
 */

class MobileOptimizedApp {
    constructor() {
        this.cache = new Map();
        this.isOnline = navigator.onLine;
        this.touchStartY = 0;
        this.pullToRefreshEnabled = false;
        this.debounceTimers = new Map();
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupOfflineHandling();
        this.setupPullToRefresh();
        this.setupTouchOptimizations();
        this.loadDashboardData();
    }

    setupEventListeners() {
        // Network status
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.syncOfflineData();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showOfflineMessage();
        });

        // Mobile navigation
        const menuToggle = document.querySelector('.menu-toggle');
        if (menuToggle) {
            menuToggle.addEventListener('click', this.toggleMobileMenu.bind(this));
        }

        // Search with debouncing
        const searchInput = document.querySelector('#mobile-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.performSearch(e.target.value);
            }, 300));
        }

        // Form submissions with loading states
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', this.handleFormSubmit.bind(this));
        });
    }

    setupOfflineHandling() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/service-worker.js')
                .catch(err => console.log('SW registration failed'));
        }
    }

    setupPullToRefresh() {
        const container = document.querySelector('.mobile-container');
        if (!container) return;

        container.addEventListener('touchstart', (e) => {
            this.touchStartY = e.touches[0].clientY;
        });

        container.addEventListener('touchmove', (e) => {
            const touchY = e.touches[0].clientY;
            const touchDiff = touchY - this.touchStartY;

            if (touchDiff > 0 && window.scrollY === 0) {
                this.pullToRefreshEnabled = true;
                this.showPullToRefreshIndicator(touchDiff);
            }
        });

        container.addEventListener('touchend', () => {
            if (this.pullToRefreshEnabled) {
                this.triggerRefresh();
                this.pullToRefreshEnabled = false;
            }
            this.hidePullToRefreshIndicator();
        });
    }

    setupTouchOptimizations() {
        // Add touch feedback to interactive elements
        const interactiveElements = document.querySelectorAll('.mobile-card, .mobile-list-item, .btn-mobile');
        
        interactiveElements.forEach(element => {
            element.addEventListener('touchstart', () => {
                element.classList.add('touch-active');
            });
            
            element.addEventListener('touchend', () => {
                setTimeout(() => {
                    element.classList.remove('touch-active');
                }, 150);
            });
        });
    }

    async loadDashboardData() {
        try {
            this.showLoading('dashboard-stats');
            
            const response = await this.fetchWithCache('/api/v2/dashboard/stats', 60000);
            if (response.success) {
                this.updateDashboardStats(response.data);
            }
            
            this.loadRecentScans();
        } catch (error) {
            this.handleError('Failed to load dashboard data', error);
        } finally {
            this.hideLoading('dashboard-stats');
        }
    }

    async loadRecentScans() {
        try {
            this.showLoading('recent-scans');
            
            const response = await this.fetchWithCache('/api/v2/scans/recent?limit=10', 30000);
            if (response.success) {
                this.updateRecentScans(response.data);
            }
        } catch (error) {
            this.handleError('Failed to load recent scans', error);
        } finally {
            this.hideLoading('recent-scans');
        }
    }

    async fetchWithCache(url, cacheDuration = 60000) {
        const cacheKey = url;
        const cached = this.cache.get(cacheKey);
        
        if (cached && (Date.now() - cached.timestamp) < cacheDuration) {
            return cached.data;
        }

        if (!this.isOnline) {
            if (cached) return cached.data;
            throw new Error('No network connection and no cached data');
        }

        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        
        this.cache.set(cacheKey, {
            data,
            timestamp: Date.now()
        });

        return data;
    }

    updateDashboardStats(data) {
        const overview = data.overview;
        
        // Update stat cards
        this.updateStatCard('total-parent-bags', overview.total_parent_bags || 0);
        this.updateStatCard('total-child-bags', overview.total_child_bags || 0);
        this.updateStatCard('total-scans', overview.total_scans || 0);
        this.updateStatCard('today-scans', data.today_scans || 0);

        // Update activity trend chart if exists
        if (data.activity_trend && data.activity_trend.length > 0) {
            this.updateActivityChart(data.activity_trend);
        }
    }

    updateStatCard(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            const valueElement = element.querySelector('.stat-value-mobile');
            if (valueElement) {
                this.animateNumber(valueElement, value);
            }
        }
    }

    animateNumber(element, targetValue) {
        const startValue = parseInt(element.textContent) || 0;
        const duration = 1000;
        const startTime = Date.now();

        const animate = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const currentValue = Math.round(startValue + (targetValue - startValue) * easeOutQuart);
            
            element.textContent = currentValue.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }

    updateRecentScans(scans) {
        const container = document.getElementById('recent-scans-list');
        if (!container) return;

        container.innerHTML = '';

        if (!scans || scans.length === 0) {
            container.innerHTML = '<div class="no-data-mobile">No recent scans found</div>';
            return;
        }

        scans.forEach(scan => {
            const scanElement = this.createScanElement(scan);
            container.appendChild(scanElement);
        });
    }

    createScanElement(scan) {
        const element = document.createElement('div');
        element.className = 'mobile-list-item';
        
        const timeAgo = this.getTimeAgo(new Date(scan.timestamp));
        const typeIcon = scan.type === 'parent' ? '📦' : '📋';
        
        element.innerHTML = `
            <div class="mobile-list-item-content">
                <div class="mobile-list-item-title">${typeIcon} ${scan.bag_qr}</div>
                <div class="mobile-list-item-subtitle">by ${scan.user} • ${timeAgo}</div>
            </div>
            <div class="mobile-list-item-action">→</div>
        `;

        element.addEventListener('click', () => {
            this.viewScanDetails(scan.id);
        });

        return element;
    }

    async performSearch(query) {
        if (query.length < 2) {
            this.clearSearchResults();
            return;
        }

        try {
            this.showLoading('search-results');
            
            const response = await this.fetchWithCache(
                `/api/mobile/bags/search?q=${encodeURIComponent(query)}&limit=20`,
                10000
            );
            
            if (response.success) {
                this.displaySearchResults(response.data);
            }
        } catch (error) {
            this.handleError('Search failed', error);
        } finally {
            this.hideLoading('search-results');
        }
    }

    displaySearchResults(results) {
        const container = document.getElementById('search-results');
        if (!container) return;

        container.innerHTML = '';

        if (!results || results.length === 0) {
            container.innerHTML = '<div class="no-data-mobile">No bags found</div>';
            return;
        }

        results.forEach(bag => {
            const bagElement = this.createBagElement(bag);
            container.appendChild(bagElement);
        });

        container.style.display = 'block';
    }

    createBagElement(bag) {
        const element = document.createElement('div');
        element.className = 'mobile-list-item';
        
        const typeIcon = bag.type === 'parent' ? '📦' : '📋';
        const subtitle = bag.type === 'child' && bag.parent_qr 
            ? `Child of ${bag.parent_qr}` 
            : bag.type.charAt(0).toUpperCase() + bag.type.slice(1) + ' bag';
        
        element.innerHTML = `
            <div class="mobile-list-item-content">
                <div class="mobile-list-item-title">${typeIcon} ${bag.qr_id}</div>
                <div class="mobile-list-item-subtitle">${subtitle}</div>
            </div>
            <div class="mobile-list-item-action">→</div>
        `;

        element.addEventListener('click', () => {
            this.viewBagDetails(bag.type, bag.qr_id);
        });

        return element;
    }

    async submitScan(qrCode) {
        try {
            this.showLoading('scan-submit');
            
            const response = await fetch('/api/mobile/scan/submit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify({
                    qr_code: qrCode,
                    type: 'manual'
                })
            });

            const data = await response.json();
            
            if (data.success) {
                this.showSuccess(`Successfully scanned ${data.data.bag_type} bag ${data.data.bag_qr}`);
                this.clearCache();
                this.loadDashboardData();
            } else {
                this.showError(data.error || 'Scan failed');
            }
        } catch (error) {
            this.handleError('Scan submission failed', error);
        } finally {
            this.hideLoading('scan-submit');
        }
    }

    // Utility methods
    debounce(func, wait) {
        return (...args) => {
            const key = func.toString();
            clearTimeout(this.debounceTimers.get(key));
            this.debounceTimers.set(key, setTimeout(() => func.apply(this, args), wait));
        };
    }

    getTimeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
        return `${Math.floor(diffInSeconds / 86400)}d ago`;
    }

    showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="loading-mobile">
                    <div class="spinner-mobile"></div>
                    Loading...
                </div>
            `;
        }
    }

    hideLoading(elementId) {
        // Loading will be replaced by actual content
    }

    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    showError(message) {
        this.showAlert(message, 'danger');
    }

    showAlert(message, type = 'info') {
        const alertContainer = document.getElementById('alert-container') || document.body;
        const alert = document.createElement('div');
        alert.className = `alert-mobile alert-${type}`;
        alert.textContent = message;
        
        alertContainer.appendChild(alert);
        
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }

    handleError(message, error) {
        console.error(message, error);
        this.showError(message);
    }

    toggleMobileMenu() {
        const menu = document.getElementById('mobile-menu');
        if (menu) {
            menu.classList.toggle('show');
        }
    }

    showPullToRefreshIndicator(distance) {
        let indicator = document.getElementById('pull-refresh-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'pull-refresh-indicator';
            indicator.className = 'pull-refresh-mobile';
            indicator.textContent = 'Pull to refresh';
            document.body.insertBefore(indicator, document.body.firstChild);
        }
        
        const opacity = Math.min(distance / 100, 1);
        indicator.style.opacity = opacity;
        indicator.style.transform = `translateY(${Math.min(distance, 60)}px)`;
    }

    hidePullToRefreshIndicator() {
        const indicator = document.getElementById('pull-refresh-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    triggerRefresh() {
        this.clearCache();
        this.loadDashboardData();
        this.showSuccess('Data refreshed');
    }

    clearCache() {
        this.cache.clear();
    }

    clearSearchResults() {
        const container = document.getElementById('search-results');
        if (container) {
            container.style.display = 'none';
            container.innerHTML = '';
        }
    }

    showOfflineMessage() {
        this.showAlert('You are offline. Some features may not be available.', 'warning');
    }

    async syncOfflineData() {
        // Sync any pending offline data when back online
        this.showSuccess('Back online! Syncing data...');
        this.clearCache();
        this.loadDashboardData();
    }

    handleFormSubmit(event) {
        const form = event.target;
        const submitButton = form.querySelector('button[type="submit"]');
        
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<div class="spinner-mobile"></div> Processing...';
            
            // Re-enable after 5 seconds as fallback
            setTimeout(() => {
                submitButton.disabled = false;
                submitButton.innerHTML = submitButton.dataset.originalText || 'Submit';
            }, 5000);
        }
    }

    updateActivityChart(data) {
        // Simple chart implementation for mobile
        const chartContainer = document.getElementById('activity-chart');
        if (!chartContainer) return;

        const maxValue = Math.max(...data.map(d => d.count));
        const chartHTML = data.map(item => {
            const height = maxValue > 0 ? (item.count / maxValue) * 100 : 0;
            const date = new Date(item.date).toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric' 
            });
            
            return `
                <div class="chart-bar">
                    <div class="chart-bar-fill" style="height: ${height}%"></div>
                    <div class="chart-bar-label">${date}</div>
                    <div class="chart-bar-value">${item.count}</div>
                </div>
            `;
        }).join('');

        chartContainer.innerHTML = `<div class="simple-chart">${chartHTML}</div>`;
    }

    viewBagDetails(type, qrId) {
        window.location.href = `/api/v2/bags/${type}/${qrId}/details`;
    }

    viewScanDetails(scanId) {
        // Implementation for viewing scan details
        console.log('View scan details:', scanId);
    }
}

// Initialize the mobile app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.mobileApp = new MobileOptimizedApp();
});

// QR Code scanner integration
if (typeof Html5QrcodeScanner !== 'undefined') {
    function initQRScanner() {
        const scanner = new Html5QrcodeScanner(
            "qr-scanner",
            { 
                fps: 10, 
                qrbox: { width: 250, height: 250 },
                aspectRatio: 1.0
            }
        );
        
        scanner.render((decodedText) => {
            scanner.clear();
            if (window.mobileApp) {
                window.mobileApp.submitScan(decodedText);
            }
        }, (error) => {
            console.log('QR scan error:', error);
        });
    }
}

// Export for global access
window.MobileOptimizedApp = MobileOptimizedApp;