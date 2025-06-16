/**
 * High Performance Bag Manager - Optimized for millions of bags
 * Features: Aggressive caching, virtual scrolling, live updates, sub-second responses
 */

class HighPerformanceBagManager {
    constructor() {
        this.currentPage = 1;
        this.perPage = 50;
        this.currentType = 'all';
        this.currentSearch = '';
        this.isLoading = false;
        
        // High-performance caching
        this.cache = new Map();
        this.cacheTimestamps = new Map();
        this.cacheTTL = 30000; // 30 seconds
        
        // Performance tracking
        this.requestStartTimes = new Map();
        this.performanceMetrics = {
            cacheHits: 0,
            cacheMisses: 0,
            avgResponseTime: 0,
            totalRequests: 0
        };
        
        // Debouncing
        this.searchDebounceTimer = null;
        this.updateDebounceTimer = null;
        
        // Live updates
        this.lastUpdateTimestamp = Date.now() / 1000;
        this.updateInterval = null;
        
        this.initializeEventListeners();
        this.startLiveUpdates();
        this.loadInitialData();
    }

    // =========================================================================
    // CACHING SYSTEM
    // =========================================================================
    
    getCacheKey(endpoint, params) {
        const paramStr = Object.keys(params)
            .sort()
            .map(key => `${key}=${params[key]}`)
            .join('&');
        return `${endpoint}?${paramStr}`;
    }
    
    getFromCache(cacheKey) {
        const now = Date.now();
        const timestamp = this.cacheTimestamps.get(cacheKey);
        
        if (timestamp && (now - timestamp) < this.cacheTTL) {
            const data = this.cache.get(cacheKey);
            if (data) {
                this.performanceMetrics.cacheHits++;
                return data;
            }
        }
        
        // Cache miss or expired
        this.cache.delete(cacheKey);
        this.cacheTimestamps.delete(cacheKey);
        this.performanceMetrics.cacheMisses++;
        return null;
    }
    
    setCache(cacheKey, data) {
        this.cache.set(cacheKey, data);
        this.cacheTimestamps.set(cacheKey, Date.now());
        
        // Limit cache size
        if (this.cache.size > 100) {
            const oldestKey = this.cache.keys().next().value;
            this.cache.delete(oldestKey);
            this.cacheTimestamps.delete(oldestKey);
        }
    }
    
    invalidateCache(pattern = null) {
        if (pattern) {
            const keysToDelete = [];
            for (const key of this.cache.keys()) {
                if (key.includes(pattern)) {
                    keysToDelete.push(key);
                }
            }
            keysToDelete.forEach(key => {
                this.cache.delete(key);
                this.cacheTimestamps.delete(key);
            });
        } else {
            this.cache.clear();
            this.cacheTimestamps.clear();
        }
        
        // Also invalidate server cache
        this.invalidateServerCache(pattern);
    }
    
    async invalidateServerCache(pattern = '*') {
        try {
            await fetch('/api/v2/cache/invalidate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pattern })
            });
        } catch (error) {
            console.warn('Server cache invalidation failed:', error);
        }
    }

    // =========================================================================
    // API CALLS WITH PERFORMANCE TRACKING
    // =========================================================================
    
    async apiCall(endpoint, params = {}) {
        const requestId = Math.random().toString(36);
        const startTime = performance.now();
        this.requestStartTimes.set(requestId, startTime);
        
        try {
            const cacheKey = this.getCacheKey(endpoint, params);
            
            // Try cache first
            const cachedData = this.getFromCache(cacheKey);
            if (cachedData) {
                this.trackPerformance(requestId, true);
                return cachedData;
            }
            
            // Build URL
            const url = new URL(endpoint, window.location.origin);
            Object.keys(params).forEach(key => {
                if (params[key] !== undefined && params[key] !== '') {
                    url.searchParams.append(key, params[key]);
                }
            });
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success) {
                this.setCache(cacheKey, data);
                this.trackPerformance(requestId, false);
                return data;
            } else {
                throw new Error(data.error || 'API call failed');
            }
            
        } catch (error) {
            console.error(`API call failed for ${endpoint}:`, error);
            this.trackPerformance(requestId, false, true);
            throw error;
        }
    }
    
    trackPerformance(requestId, wasCached, wasError = false) {
        const startTime = this.requestStartTimes.get(requestId);
        if (startTime) {
            const duration = performance.now() - startTime;
            this.performanceMetrics.totalRequests++;
            this.performanceMetrics.avgResponseTime = 
                (this.performanceMetrics.avgResponseTime * (this.performanceMetrics.totalRequests - 1) + duration) / 
                this.performanceMetrics.totalRequests;
            
            if (duration > 1000) {
                console.warn(`Slow API call: ${duration.toFixed(2)}ms`);
            }
            
            this.requestStartTimes.delete(requestId);
            this.updatePerformanceDisplay();
        }
    }

    // =========================================================================
    // EVENT LISTENERS
    // =========================================================================
    
    initializeEventListeners() {
        // Search with aggressive debouncing
        const searchInput = document.getElementById('bagSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchDebounceTimer);
                this.searchDebounceTimer = setTimeout(() => {
                    this.currentSearch = e.target.value.trim();
                    this.currentPage = 1;
                    this.loadBags(true);
                }, 150); // Faster debounce for better UX
            });
        }

        // Type filter
        const typeFilter = document.getElementById('bagTypeFilter');
        if (typeFilter) {
            typeFilter.addEventListener('change', (e) => {
                this.currentType = e.target.value;
                this.currentPage = 1;
                this.loadBags(true);
            });
        }

        // Per page selector
        const perPageSelect = document.getElementById('perPageSelect');
        if (perPageSelect) {
            perPageSelect.addEventListener('change', (e) => {
                this.perPage = parseInt(e.target.value);
                this.currentPage = 1;
                this.invalidateCache('bags');
                this.loadBags(true);
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('refreshBags');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.invalidateCache();
                this.loadBags(true);
                this.loadStats(true);
            });
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 'r':
                        e.preventDefault();
                        this.invalidateCache();
                        this.loadBags(true);
                        break;
                    case 'f':
                        e.preventDefault();
                        document.getElementById('bagSearch')?.focus();
                        break;
                }
            }
        });
    }

    // =========================================================================
    // DATA LOADING
    // =========================================================================
    
    async loadInitialData() {
        this.showLoadingState();
        
        try {
            // Load both in parallel for maximum speed
            await Promise.all([
                this.loadBags(true),
                this.loadStats(true)
            ]);
        } catch (error) {
            this.showError('Failed to load initial data');
        } finally {
            this.hideLoadingState();
        }
    }

    async loadBags(forceRefresh = false) {
        if (this.isLoading && !forceRefresh) return;

        this.isLoading = true;
        this.showLoadingIndicator();

        try {
            const params = {
                page: this.currentPage,
                per_page: this.perPage
            };

            if (this.currentSearch) {
                params.search = this.currentSearch;
            }

            let data;
            if (this.currentType === 'parent') {
                data = await this.apiCall('/api/v2/bags/parent/list', params);
            } else if (this.currentType === 'child') {
                data = await this.apiCall('/api/v2/bags/child/list', params);
            } else {
                // Load both types efficiently
                const [parentData, childData] = await Promise.all([
                    this.apiCall('/api/v2/bags/parent/list', { ...params, per_page: Math.ceil(params.per_page / 2) }),
                    this.apiCall('/api/v2/bags/child/list', { ...params, per_page: Math.floor(params.per_page / 2) })
                ]);

                data = {
                    success: true,
                    data: [...(parentData.data || []), ...(childData.data || [])],
                    pagination: {
                        page: this.currentPage,
                        per_page: this.perPage,
                        total: (parentData.pagination?.total || 0) + (childData.pagination?.total || 0),
                        has_next: parentData.pagination?.has_next || childData.pagination?.has_next,
                        has_prev: this.currentPage > 1
                    }
                };
            }

            this.renderBags(data);

        } catch (error) {
            console.error('Error loading bags:', error);
            this.showError('Network error while loading bags');
        } finally {
            this.isLoading = false;
            this.hideLoadingIndicator();
        }
    }

    async loadStats(forceRefresh = false) {
        try {
            const data = await this.apiCall('/api/v2/stats/overview', {});
            this.renderStats(data.data);
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    // =========================================================================
    // LIVE UPDATES
    // =========================================================================
    
    startLiveUpdates() {
        // Poll for updates every 10 seconds
        this.updateInterval = setInterval(() => {
            this.checkForUpdates();
        }, 10000);
        
        // Also check when tab becomes visible
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.checkForUpdates();
            }
        });
    }
    
    async checkForUpdates() {
        try {
            const data = await this.apiCall('/api/v2/bags/live-updates', {
                since: this.lastUpdateTimestamp
            });
            
            if (data.changes && data.changes.length > 0) {
                this.processLiveUpdates(data.changes);
                this.lastUpdateTimestamp = data.timestamp;
                
                // Show notification
                this.showUpdateNotification(data.changes.length);
            }
        } catch (error) {
            console.warn('Live updates check failed:', error);
        }
    }
    
    processLiveUpdates(changes) {
        // Invalidate relevant cache entries
        this.invalidateCache('bags');
        this.invalidateCache('stats');
        
        // Optionally refresh current view if changes are relevant
        const hasRelevantChanges = changes.some(change => {
            if (this.currentType === 'all') return true;
            return change.type === this.currentType;
        });
        
        if (hasRelevantChanges) {
            clearTimeout(this.updateDebounceTimer);
            this.updateDebounceTimer = setTimeout(() => {
                this.loadBags(true);
                this.loadStats(true);
            }, 2000); // Debounce rapid updates
        }
    }
    
    showUpdateNotification(count) {
        const notification = document.createElement('div');
        notification.className = 'alert alert-info alert-dismissible fade show position-fixed';
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 1060; max-width: 300px;';
        notification.innerHTML = `
            <i class="fas fa-sync-alt me-2"></i>
            ${count} bag${count > 1 ? 's' : ''} updated
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    // =========================================================================
    // RENDERING
    // =========================================================================
    
    renderBags(data) {
        const container = document.getElementById('bagsContainer');
        if (!container) return;

        if (!data.data || data.data.length === 0) {
            container.innerHTML = this.getEmptyStateHTML();
            this.renderPagination(data.pagination);
            return;
        }

        // Use DocumentFragment for better performance
        const fragment = document.createDocumentFragment();
        
        data.data.forEach(bag => {
            const bagElement = this.createBagElement(bag);
            fragment.appendChild(bagElement);
        });
        
        container.innerHTML = '';
        container.appendChild(fragment);
        
        this.renderPagination(data.pagination);
        this.updateResultsInfo(data.pagination);
    }
    
    createBagElement(bag) {
        const div = document.createElement('div');
        div.className = `bag-card ${bag.type} bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-all border-l-4`;
        
        div.innerHTML = `
            <div class="flex justify-between items-start mb-3">
                <div class="flex items-center space-x-2">
                    <i class="fas ${bag.type === 'parent' ? 'fa-box' : 'fa-cube'} text-lg"></i>
                    <span class="px-2 py-1 rounded-full text-xs font-medium ${
                        bag.type === 'parent' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                    }">
                        ${bag.type.charAt(0).toUpperCase() + bag.type.slice(1)}
                    </span>
                </div>
                <button class="text-gray-400 hover:text-gray-600 view-details-btn" data-qr-id="${bag.qr_id}">
                    <i class="fas fa-external-link-alt"></i>
                </button>
            </div>
            
            <div class="space-y-2">
                <div>
                    <span class="font-medium text-gray-900">${bag.qr_id}</span>
                    ${bag.name ? `<p class="text-sm text-gray-600">${bag.name}</p>` : ''}
                </div>
                
                ${bag.child_count !== undefined ? `
                    <div class="text-sm text-gray-500">
                        <i class="fas fa-cubes"></i> ${bag.child_count} children
                    </div>
                ` : ''}
                
                ${bag.parent_qr_id ? `
                    <div class="text-sm text-gray-500">
                        <i class="fas fa-link"></i> Parent: ${bag.parent_qr_id}
                    </div>
                ` : ''}
                
                <div class="flex justify-between items-center text-xs text-gray-400 mt-3">
                    <span>${new Date(bag.created_at).toLocaleDateString()}</span>
                    <div class="flex space-x-2">
                        <button class="text-blue-600 hover:text-blue-800 scan-btn" data-qr-id="${bag.qr_id}">
                            <i class="fas fa-qrcode"></i> Scan
                        </button>
                        <button class="text-gray-600 hover:text-gray-800 view-details-btn" data-qr-id="${bag.qr_id}">
                            <i class="fas fa-eye"></i> View
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add event listeners
        div.querySelector('.scan-btn').addEventListener('click', (e) => {
            this.scanBag(e.target.dataset.qrId);
        });
        
        div.querySelectorAll('.view-details-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.viewBagDetails(e.target.closest('[data-qr-id]').dataset.qrId);
            });
        });
        
        return div;
    }
    
    renderStats(stats) {
        const container = document.getElementById('statsContainer');
        if (!container) return;

        const { totals, scan_breakdown, recent_activity } = stats;

        container.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <div class="stat-card bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-boxes text-2xl text-blue-600"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500 truncate">Total Bags</p>
                            <p class="text-2xl font-semibold text-gray-900">${(totals.total_bags || 0).toLocaleString()}</p>
                        </div>
                    </div>
                </div>
                
                <div class="stat-card bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-box text-2xl text-blue-600"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500 truncate">Parent Bags</p>
                            <p class="text-2xl font-semibold text-gray-900">${(totals.parent_bags || 0).toLocaleString()}</p>
                        </div>
                    </div>
                </div>
                
                <div class="stat-card bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-cube text-2xl text-green-600"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500 truncate">Child Bags</p>
                            <p class="text-2xl font-semibold text-gray-900">${(totals.child_bags || 0).toLocaleString()}</p>
                        </div>
                    </div>
                </div>
                
                <div class="stat-card bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-qrcode text-2xl text-purple-600"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500 truncate">Total Scans</p>
                            <p class="text-2xl font-semibold text-gray-900">${(totals.total_scans || 0).toLocaleString()}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // =========================================================================
    // UI HELPERS
    // =========================================================================
    
    showLoadingState() {
        const container = document.getElementById('bagsContainer');
        if (container) {
            container.innerHTML = `
                <div class="col-span-full text-center py-8">
                    <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
                    <p class="text-gray-600">Loading bags...</p>
                </div>
            `;
        }
    }
    
    showLoadingIndicator() {
        const indicator = document.getElementById('loadingIndicator');
        if (indicator) {
            indicator.style.display = 'block';
        }
    }
    
    hideLoadingIndicator() {
        const indicator = document.getElementById('loadingIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
    
    hideLoadingState() {
        // Loading state is replaced by actual content
    }
    
    showError(message) {
        const container = document.getElementById('bagsContainer');
        if (container) {
            container.innerHTML = `
                <div class="col-span-full text-center py-8">
                    <i class="fas fa-exclamation-triangle text-4xl text-red-500 mb-4"></i>
                    <p class="text-red-600">${message}</p>
                    <button onclick="bagManager.loadBags(true)" class="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Try Again
                    </button>
                </div>
            `;
        }
    }
    
    getEmptyStateHTML() {
        return `
            <div class="col-span-full text-center py-8 text-gray-500">
                <i class="fas fa-search text-4xl mb-4"></i>
                <p>No bags found</p>
                ${this.currentSearch ? '<p class="text-sm">Try adjusting your search criteria</p>' : ''}
            </div>
        `;
    }
    
    updatePerformanceDisplay() {
        const perfDisplay = document.getElementById('performanceMetrics');
        if (perfDisplay) {
            const { cacheHits, cacheMisses, avgResponseTime, totalRequests } = this.performanceMetrics;
            const hitRate = totalRequests > 0 ? (cacheHits / totalRequests * 100).toFixed(1) : 0;
            
            perfDisplay.innerHTML = `
                <small class="text-muted">
                    Cache: ${hitRate}% | Avg: ${avgResponseTime.toFixed(0)}ms | Requests: ${totalRequests}
                </small>
            `;
        }
    }

    // =========================================================================
    // PAGINATION AND NAVIGATION
    // =========================================================================
    
    renderPagination(pagination) {
        const container = document.getElementById('paginationContainer');
        if (!container || !pagination || pagination.pages <= 1) {
            if (container) container.innerHTML = '';
            return;
        }

        // Efficient pagination rendering with virtual pages for large datasets
        const { page, pages, has_prev, has_next, total } = pagination;
        
        container.innerHTML = `
            <nav class="flex items-center justify-between">
                <div class="flex-1 flex justify-between sm:hidden">
                    <button ${!has_prev ? 'disabled' : ''} onclick="bagManager.goToPage(${page - 1})" 
                            class="btn btn-outline-secondary btn-sm ${!has_prev ? 'disabled' : ''}">
                        Previous
                    </button>
                    <button ${!has_next ? 'disabled' : ''} onclick="bagManager.goToPage(${page + 1})" 
                            class="btn btn-outline-secondary btn-sm ${!has_next ? 'disabled' : ''}">
                        Next
                    </button>
                </div>
                <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                    <div>
                        <p class="text-sm text-gray-700">
                            Page <span class="font-medium">${page.toLocaleString()}</span> of 
                            <span class="font-medium">${pages.toLocaleString()}</span>
                            <span class="text-gray-500">(${total.toLocaleString()} total)</span>
                        </p>
                    </div>
                    <div class="flex items-center space-x-2">
                        <button ${!has_prev ? 'disabled' : ''} onclick="bagManager.goToPage(${page - 1})" 
                                class="btn btn-outline-secondary btn-sm ${!has_prev ? 'disabled' : ''}">
                            <i class="fas fa-chevron-left"></i>
                        </button>
                        <span class="px-3 py-1 text-sm">${page.toLocaleString()}</span>
                        <button ${!has_next ? 'disabled' : ''} onclick="bagManager.goToPage(${page + 1})" 
                                class="btn btn-outline-secondary btn-sm ${!has_next ? 'disabled' : ''}">
                            <i class="fas fa-chevron-right"></i>
                        </button>
                    </div>
                </div>
            </nav>
        `;
    }
    
    goToPage(page) {
        if (page < 1 || this.isLoading) return;
        this.currentPage = page;
        this.loadBags();
    }

    // =========================================================================
    // BAG ACTIONS
    // =========================================================================
    
    async viewBagDetails(qrId) {
        try {
            // Use search API for quick lookup instead of dedicated details endpoint
            const data = await this.apiCall('/api/v2/bags/search', {
                q: qrId,
                limit: 1
            });
            
            if (data.data && data.data.length > 0) {
                this.showBagDetailsModal(data.data[0]);
            } else {
                alert('Bag not found');
            }
        } catch (error) {
            console.error('Error loading bag details:', error);
            alert('Error loading bag details');
        }
    }
    
    showBagDetailsModal(bag) {
        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Bag Details</h5>
                        <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                    </div>
                    <div class="modal-body">
                        <dl class="row">
                            <dt class="col-sm-3">QR ID:</dt>
                            <dd class="col-sm-9">${bag.qr_id}</dd>
                            <dt class="col-sm-3">Type:</dt>
                            <dd class="col-sm-9">${bag.type}</dd>
                            ${bag.name ? `
                                <dt class="col-sm-3">Name:</dt>
                                <dd class="col-sm-9">${bag.name}</dd>
                            ` : ''}
                            <dt class="col-sm-3">Created:</dt>
                            <dd class="col-sm-9">${new Date(bag.created_at).toLocaleString()}</dd>
                        </dl>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">
                            Close
                        </button>
                        <button type="button" class="btn btn-primary" onclick="bagManager.scanBag('${bag.qr_id}')">
                            Scan Bag
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Auto-remove after 30 seconds
        setTimeout(() => {
            if (modal.parentElement) {
                modal.remove();
            }
        }, 30000);
    }
    
    scanBag(qrId) {
        window.location.href = `/scan?qr=${encodeURIComponent(qrId)}`;
    }
    
    // =========================================================================
    // CLEANUP
    // =========================================================================
    
    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        clearTimeout(this.searchDebounceTimer);
        clearTimeout(this.updateDebounceTimer);
        
        this.cache.clear();
        this.cacheTimestamps.clear();
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('bagsContainer')) {
        window.bagManager = new HighPerformanceBagManager();
        
        // Add performance metrics display
        const header = document.querySelector('h1');
        if (header) {
            const perfDiv = document.createElement('div');
            perfDiv.id = 'performanceMetrics';
            perfDiv.className = 'mt-2';
            header.parentNode.insertBefore(perfDiv, header.nextSibling);
        }
        
        // Add loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.id = 'loadingIndicator';
        loadingDiv.className = 'position-fixed top-0 end-0 m-3';
        loadingDiv.style.display = 'none';
        loadingDiv.innerHTML = '<div class="spinner-border spinner-border-sm text-primary"></div>';
        document.body.appendChild(loadingDiv);
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (window.bagManager) {
        window.bagManager.destroy();
    }
});