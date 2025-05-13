/**
 * TraceTrack Application JS
 * Core functionality for the TraceTrack application
 * Optimized for high-performance and multiple concurrent users
 */

// Use strict mode for better error checking and performance
'use strict';

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            delay: { show: 500, hide: 100 }
        });
    });

    // Initialize all popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl, {
            trigger: 'hover focus'
        });
    });
    
    // Setup flash message auto-dismiss after 5 seconds
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Activate form validation styles
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Add event listener for bill search modal
    setupBillSearchModal();
    
    // Setup any QR code scanners on the page
    setupQRScanners();
    
    // Setup any data tables on the page
    setupDataTables();
});

/**
 * Setup the bill search modal functionality
 */
function setupBillSearchModal() {
    const searchBillBtn = document.getElementById('searchBillBtn');
    const billIdInput = document.getElementById('billIdSearch');
    const searchBillForm = document.getElementById('searchBillForm');
    
    if (searchBillBtn && billIdInput && searchBillForm) {
        searchBillBtn.addEventListener('click', function() {
            if (billIdInput.value.trim() !== '') {
                const billId = billIdInput.value.trim();
                const action = searchBillForm.action.replace('PLACEHOLDER', encodeURIComponent(billId));
                window.location.href = action;
            }
        });
        
        billIdInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchBillBtn.click();
            }
        });
    }
}

/**
 * Setup QR code scanners if present on the page
 */
function setupQRScanners() {
    // This function will be populated when the QR scanner is needed
    // It's a placeholder for now to maintain structure
}

/**
 * Setup data tables for any table with the 'data-table' class
 */
function setupDataTables() {
    const tables = document.querySelectorAll('table.data-table');
    if (tables.length === 0) return;
    
    // This function would be populated when DataTables.js is loaded
    // It's a placeholder for now
}

/**
 * Format date objects or ISO strings to a human-readable format
 * @param {Date|string} date - Date object or ISO string
 * @param {boolean} includeTime - Whether to include the time
 * @returns {string} Formatted date string
 */
function formatDate(date, includeTime = true) {
    if (!date) return '';
    
    if (typeof date === 'string') {
        date = new Date(date);
    }
    
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    };
    
    if (includeTime) {
        options.hour = '2-digit';
        options.minute = '2-digit';
    }
    
    return date.toLocaleDateString(undefined, options);
}

/**
 * Debounce function to limit how often a function can be called
 * Useful for search inputs and window resize events
 * @param {Function} func - The function to debounce
 * @param {number} wait - The time to wait in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait = 300) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}