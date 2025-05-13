document.addEventListener('DOMContentLoaded', function() {
    const mapContainer = document.getElementById('location-map');
    
    if (!mapContainer) return;
    
    // Initialize locations map
    initializeLocationsMap();
    
    function initializeLocationsMap() {
        // Get locations from API
        fetch('/api/locations')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.locations && data.locations.length > 0) {
                    renderMap(data.locations);
                } else {
                    showMapError('No location data available');
                }
            })
            .catch(error => {
                console.error('Error fetching locations:', error);
                showMapError('Failed to load location data');
            });
    }
    
    function renderMap(locations) {
        // Check if we have locations with coordinates
        const locationsWithCoords = locations.filter(location => 
            location.latitude && location.longitude
        );
        
        if (locationsWithCoords.length === 0) {
            showMapError('No location coordinates available for mapping');
            return;
        }
        
        // Initialize Leaflet map
        const map = L.map('location-map');
        
        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        
        // Track bounds for auto-zooming
        const bounds = L.latLngBounds();
        
        // Add markers for each location
        locationsWithCoords.forEach(location => {
            // Create marker with a different icon based on location type
            let markerIcon;
            let iconColor;
            
            switch (location.location_type) {
                case 'warehouse':
                    iconColor = 'success';
                    break;
                case 'distribution':
                    iconColor = 'primary';
                    break;
                case 'retail':
                    iconColor = 'info';
                    break;
                default:
                    iconColor = 'secondary';
            }
            
            // Create marker
            const marker = L.marker([location.latitude, location.longitude])
                .bindPopup(`
                    <strong>${location.name}</strong><br>
                    ${location.address || ''}<br>
                    Type: ${location.location_type || 'Unknown'}
                `);
            
            marker.addTo(map);
            
            // Extend bounds to include this marker
            bounds.extend([location.latitude, location.longitude]);
        });
        
        // Fit map to all markers
        if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [30, 30] });
        } else {
            // Fallback to a default view if bounds aren't valid
            map.setView([0, 0], 2);
        }
    }
    
    function showMapError(message) {
        mapContainer.innerHTML = `
            <div class="alert alert-warning m-3">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
    }
});
