// TraceTrack Application JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Location selection functionality
    const locationCards = document.querySelectorAll('.location-card');
    if (locationCards.length > 0) {
        locationCards.forEach(function(card) {
            card.addEventListener('click', function() {
                // Remove selected class from all cards
                locationCards.forEach(c => c.classList.remove('selected'));
                
                // Add selected class to clicked card
                this.classList.add('selected');
                
                // Set the location ID in the hidden input
                const locationId = this.dataset.locationId;
                document.getElementById('location_id').value = locationId;
                
                // Enable the submit button
                document.getElementById('select_location_btn').removeAttribute('disabled');
            });
        });
    }

    // Progress circles update for child bag scanning
    const updateProgressCircles = function(scannedCount, expectedCount) {
        const progressCirclesContainer = document.getElementById('progress_circles');
        if (!progressCirclesContainer) return;
        
        // Clear existing circles
        progressCirclesContainer.innerHTML = '';
        
        // Create new circles
        for (let i = 1; i <= expectedCount; i++) {
            const circle = document.createElement('div');
            circle.className = 'progress-circle' + (i <= scannedCount ? ' completed' : '');
            circle.textContent = i;
            progressCirclesContainer.appendChild(circle);
        }
        
        // Update progress text
        const progressText = document.getElementById('progress_text');
        if (progressText) {
            progressText.textContent = `${scannedCount} of ${expectedCount} bags scanned`;
        }
        
        // Enable finish button if all scanned
        const finishButton = document.getElementById('finish_scanning_btn');
        if (finishButton && scannedCount >= expectedCount) {
            finishButton.classList.remove('disabled');
            finishButton.setAttribute('href', finishButton.dataset.href);
        }
    };

    // Expose function globally for use in inline scripts
    window.updateProgressCircles = updateProgressCircles;
    
    // Toast notifications
    const showToast = function(message, type = 'success') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            // Create toast container if it doesn't exist
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(container);
        }
        
        // Create toast element
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        // Create toast content
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        // Append to container
        document.getElementById('toast-container').appendChild(toastEl);
        
        // Initialize and show toast
        const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
        toast.show();
        
        // Remove after hiding
        toastEl.addEventListener('hidden.bs.toast', function() {
            toastEl.remove();
        });
    };
    
    // Expose toast function globally
    window.showToast = showToast;
    

    
    // Form validation enhancement
    const forms = document.querySelectorAll('.needs-validation');
    if (forms.length > 0) {
        Array.from(forms).forEach(form => {
            form.addEventListener('submit', event => {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            }, false);
        });
    }
    
    // Confirm dialogs for dangerous actions
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    if (confirmButtons.length > 0) {
        confirmButtons.forEach(button => {
            button.addEventListener('click', event => {
                if (!confirm(button.dataset.confirm)) {
                    event.preventDefault();
                }
            });
        });
    }
});