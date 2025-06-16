/**
 * Optimized Bag Management JavaScript
 * Handles large datasets efficiently with pagination and lazy loading
 */

class OptimizedBagManager {
    constructor() {
        this.currentPage = 1;
        this.perPage = 50;
        this.currentType = 'all';
        this.currentSearch = '';
        this.isLoading = false;
        this.cache = new Map();
        this.debounceTimer = null;
        
        this.initializeEventListeners();
        this.loadInitialData();
    }

    initializeEventListeners() {
        // Search input with debouncing
        const searchInput = document.getElementById('bagSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => {
                    this.currentSearch = e.target.value.trim();
                    this.currentPage = 1;
                    this.loadBags(true);
                }, 300);
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
                this.loadBags(true);
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('refreshBags');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.cache.clear();
                this.loadBags(true);
                this.loadStats();
            });
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.loadBags(true),
            this.loadStats()
        ]);
    }

    async loadBags(forceRefresh = false) {
        if (this.isLoading) return;

        const cacheKey = `${this.currentType}-${this.currentPage}-${this.perPage}-${this.currentSearch}`;
        
        if (!forceRefresh && this.cache.has(cacheKey)) {
            this.renderBags(this.cache.get(cacheKey));
            return;
        }

        this.isLoading = true;
        this.showLoadingState();

        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage
            });

            if (this.currentSearch) {
                params.append('search', this.currentSearch);
            }

            let endpoint;
            if (this.currentType === 'parent') {
                endpoint = '/api/bags/parent/list';
            } else if (this.currentType === 'child') {
                endpoint = '/api/bags/child/list';
            } else {
                // Load both types and combine
                const [parentResponse, childResponse] = await Promise.all([
                    fetch(`/api/bags/parent/list?${params}`),
                    fetch(`/api/bags/child/list?${params}`)
                ]);

                const parentData = await parentResponse.json();
                const childData = await childResponse.json();

                const combinedData = {
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

                this.cache.set(cacheKey, combinedData);
                this.renderBags(combinedData);
                return;
            }

            const response = await fetch(`${endpoint}?${params}`);
            const data = await response.json();

            if (data.success) {
                this.cache.set(cacheKey, data);
                this.renderBags(data);
            } else {
                this.showError('Failed to load bags: ' + (data.error || 'Unknown error'));
            }

        } catch (error) {
            console.error('Error loading bags:', error);
            this.showError('Network error while loading bags');
        } finally {
            this.isLoading = false;
            this.hideLoadingState();
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/analytics/system-overview');
            const data = await response.json();

            if (data.success) {
                this.renderStats(data.data);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    renderBags(data) {
        const container = document.getElementById('bagsContainer');
        if (!container) return;

        if (!data.data || data.data.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-gray-500">
                    <i class="fas fa-search text-4xl mb-4"></i>
                    <p>No bags found</p>
                    ${this.currentSearch ? '<p class="text-sm">Try adjusting your search criteria</p>' : ''}
                </div>
            `;
            this.renderPagination(data.pagination);
            return;
        }

        const bagsHtml = data.data.map(bag => this.renderBagCard(bag)).join('');
        container.innerHTML = bagsHtml;
        
        this.renderPagination(data.pagination);
        this.attachBagEventListeners();
    }

    renderBagCard(bag) {
        const typeIcon = bag.type === 'parent' ? 'fas fa-box' : 'fas fa-cube';
        const typeColor = bag.type === 'parent' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800';
        
        return `
            <div class="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow border-l-4 ${bag.type === 'parent' ? 'border-blue-500' : 'border-green-500'}">
                <div class="flex justify-between items-start mb-3">
                    <div class="flex items-center space-x-2">
                        <i class="${typeIcon} text-lg ${bag.type === 'parent' ? 'text-blue-600' : 'text-green-600'}"></i>
                        <span class="px-2 py-1 rounded-full text-xs font-medium ${typeColor}">
                            ${bag.type.charAt(0).toUpperCase() + bag.type.slice(1)}
                        </span>
                    </div>
                    <button class="text-gray-400 hover:text-gray-600" onclick="bagManager.viewBagDetails('${bag.qr_id}')">
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
                            <button class="text-blue-600 hover:text-blue-800" onclick="bagManager.scanBag('${bag.qr_id}')">
                                <i class="fas fa-qrcode"></i> Scan
                            </button>
                            <button class="text-gray-600 hover:text-gray-800" onclick="bagManager.viewBagDetails('${bag.qr_id}')">
                                <i class="fas fa-eye"></i> View
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderPagination(pagination) {
        const container = document.getElementById('paginationContainer');
        if (!container || !pagination) return;

        const { page, pages, has_prev, has_next, total } = pagination;
        
        if (pages <= 1) {
            container.innerHTML = '';
            return;
        }

        let paginationHtml = `
            <div class="flex items-center justify-between bg-white px-4 py-3 sm:px-6 rounded-lg shadow">
                <div class="flex flex-1 justify-between sm:hidden">
                    <button ${!has_prev ? 'disabled' : ''} onclick="bagManager.goToPage(${page - 1})" 
                            class="relative inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50">
                        Previous
                    </button>
                    <button ${!has_next ? 'disabled' : ''} onclick="bagManager.goToPage(${page + 1})" 
                            class="relative ml-3 inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50">
                        Next
                    </button>
                </div>
                <div class="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
                    <div>
                        <p class="text-sm text-gray-700">
                            Showing page <span class="font-medium">${page}</span> of <span class="font-medium">${pages}</span>
                            <span class="text-gray-500">(${total} total bags)</span>
                        </p>
                    </div>
                    <div>
                        <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                            <button ${!has_prev ? 'disabled' : ''} onclick="bagManager.goToPage(${page - 1})" 
                                    class="relative inline-flex items-center px-2 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-l-md hover:bg-gray-50 disabled:opacity-50">
                                <i class="fas fa-chevron-left"></i>
                            </button>
        `;

        // Page numbers
        const startPage = Math.max(1, page - 2);
        const endPage = Math.min(pages, page + 2);

        for (let i = startPage; i <= endPage; i++) {
            const isActive = i === page;
            paginationHtml += `
                <button onclick="bagManager.goToPage(${i})" 
                        class="relative inline-flex items-center px-4 py-2 text-sm font-medium ${
                            isActive 
                                ? 'z-10 bg-blue-50 border-blue-500 text-blue-600' 
                                : 'text-gray-500 bg-white border-gray-300 hover:bg-gray-50'
                        }">
                    ${i}
                </button>
            `;
        }

        paginationHtml += `
                            <button ${!has_next ? 'disabled' : ''} onclick="bagManager.goToPage(${page + 1})" 
                                    class="relative inline-flex items-center px-2 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-r-md hover:bg-gray-50 disabled:opacity-50">
                                <i class="fas fa-chevron-right"></i>
                            </button>
                        </nav>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = paginationHtml;
    }

    renderStats(stats) {
        const container = document.getElementById('statsContainer');
        if (!container) return;

        const { totals, scan_breakdown, recent_activity } = stats;

        container.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-boxes text-2xl text-blue-600"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500 truncate">Total Bags</p>
                            <p class="text-2xl font-semibold text-gray-900">${totals.total_bags?.toLocaleString() || 0}</p>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-box text-2xl text-blue-600"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500 truncate">Parent Bags</p>
                            <p class="text-2xl font-semibold text-gray-900">${totals.parent_bags?.toLocaleString() || 0}</p>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-cube text-2xl text-green-600"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500 truncate">Child Bags</p>
                            <p class="text-2xl font-semibold text-gray-900">${totals.child_bags?.toLocaleString() || 0}</p>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-lg shadow p-6">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-qrcode text-2xl text-purple-600"></i>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-500 truncate">Total Scans</p>
                            <p class="text-2xl font-semibold text-gray-900">${totals.total_scans?.toLocaleString() || 0}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    attachBagEventListeners() {
        // Event listeners are handled via onclick attributes in the HTML
        // This approach is more reliable for dynamically generated content
    }

    showLoadingState() {
        const container = document.getElementById('bagsContainer');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-8">
                    <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <p class="mt-2 text-gray-600">Loading bags...</p>
                </div>
            `;
        }
    }

    hideLoadingState() {
        // Loading state is replaced by actual content
    }

    showError(message) {
        const container = document.getElementById('bagsContainer');
        if (container) {
            container.innerHTML = `
                <div class="text-center py-8">
                    <i class="fas fa-exclamation-triangle text-4xl text-red-500 mb-4"></i>
                    <p class="text-red-600">${message}</p>
                    <button onclick="bagManager.loadBags(true)" class="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Try Again
                    </button>
                </div>
            `;
        }
    }

    goToPage(page) {
        if (page < 1 || this.isLoading) return;
        this.currentPage = page;
        this.loadBags();
    }

    async viewBagDetails(qrId) {
        try {
            const response = await fetch(`/api/bags/${qrId}/details/optimized`);
            const data = await response.json();
            
            if (data.success) {
                this.showBagDetailsModal(data.data);
            } else {
                alert('Failed to load bag details');
            }
        } catch (error) {
            console.error('Error loading bag details:', error);
            alert('Error loading bag details');
        }
    }

    showBagDetailsModal(bag) {
        // Create and show modal with bag details
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50';
        modal.innerHTML = `
            <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-medium text-gray-900">Bag Details</h3>
                    <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="space-y-4">
                    <div><strong>QR ID:</strong> ${bag.qr_id}</div>
                    <div><strong>Type:</strong> ${bag.type}</div>
                    ${bag.name ? `<div><strong>Name:</strong> ${bag.name}</div>` : ''}
                    ${bag.children ? `<div><strong>Children:</strong> ${bag.children.length}</div>` : ''}
                    ${bag.parent ? `<div><strong>Parent:</strong> ${bag.parent.qr_id}</div>` : ''}
                    <div><strong>Scan Count:</strong> ${bag.scan_count || 0}</div>
                    <div><strong>Created:</strong> ${new Date(bag.created_at).toLocaleString()}</div>
                </div>
                <div class="mt-6 flex justify-end space-x-2">
                    <button onclick="this.closest('.fixed').remove()" class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">
                        Close
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    scanBag(qrId) {
        // Redirect to scan page with pre-filled QR code
        window.location.href = `/scan?qr=${encodeURIComponent(qrId)}`;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('bagsContainer')) {
        window.bagManager = new OptimizedBagManager();
    }
});