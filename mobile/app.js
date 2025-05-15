// TraceTrack Mobile App

// Initialize Capacitor if available
const { Capacitor } = window;
let isNative = false;

// Set API URL based on environment
const API_BASE_URL = 'https://your-deployed-domain.replit.app/mobile-api';
const API_KEY = 'tracetrack-mobile-key';

// App state
let appState = {
    user: null,
    locations: [],
    selectedLocation: null,
    currentParentBag: null
};

// Check if running on a device
document.addEventListener('deviceready', onDeviceReady, false);

function onDeviceReady() {
    console.log('Running on device');
    isNative = true;
    
    // Set up status bar
    if (Capacitor.isPluginAvailable('StatusBar')) {
        const { StatusBar } = Capacitor.Plugins;
        StatusBar.setBackgroundColor({ color: '#1e7a3d' });
        StatusBar.setStyle({ style: 'LIGHT' });
    }
}

// DOM elements
const loginScreen = document.getElementById('loginScreen');
const homeScreen = document.getElementById('homeScreen');
const scanResultScreen = document.getElementById('scanResultScreen');
const loginForm = document.getElementById('loginForm');
const usernameInput = document.getElementById('usernameInput');
const passwordInput = document.getElementById('passwordInput');
const loginError = document.getElementById('loginError');
const userInfo = document.getElementById('userInfo');
const usernameSpan = document.getElementById('username');
const logoutBtn = document.getElementById('logoutBtn');
const locationSelect = document.getElementById('locationSelect');
const scanParentBtn = document.getElementById('scanParentBtn');
const scanChildBtn = document.getElementById('scanChildBtn');
const scanResult = document.getElementById('scanResult');
const backToHomeBtn = document.getElementById('backToHomeBtn');

// Event listeners
document.addEventListener('DOMContentLoaded', initApp);
loginForm.addEventListener('submit', handleLogin);
logoutBtn.addEventListener('click', handleLogout);
locationSelect.addEventListener('change', handleLocationChange);
scanParentBtn.addEventListener('click', scanParentQR);
scanChildBtn.addEventListener('click', scanChildQR);
backToHomeBtn.addEventListener('click', showHomeScreen);

// Initialize the app
function initApp() {
    console.log('Initializing TraceTrack Mobile App');
    
    // Check for existing session
    const savedUser = localStorage.getItem('user');
    
    if (savedUser) {
        try {
            appState.user = JSON.parse(savedUser);
            showUserInfo();
            fetchLocations();
            showHomeScreen();
        } catch (e) {
            console.error('Error restoring session:', e);
            showLoginScreen();
        }
    } else {
        showLoginScreen();
    }
}

// Navigation functions
function showScreen(screenId) {
    // Hide all screens
    loginScreen.classList.add('d-none');
    homeScreen.classList.add('d-none');
    scanResultScreen.classList.add('d-none');
    
    // Show requested screen
    document.getElementById(screenId).classList.remove('d-none');
}

function showLoginScreen() {
    showScreen('loginScreen');
}

function showHomeScreen() {
    showScreen('homeScreen');
}

function showScanResultScreen() {
    showScreen('scanResultScreen');
}

// API functions
async function apiRequest(endpoint, method = 'GET', data = null) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-TraceTrack-Api-Key': API_KEY
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'API request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
}

// Auth functions
async function handleLogin(event) {
    event.preventDefault();
    
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();
    
    if (!username || !password) {
        showError('Please enter username and password');
        return;
    }
    
    try {
        loginError.classList.add('d-none');
        
        const data = await apiRequest('/login', 'POST', { 
            username, 
            password 
        });
        
        if (data.success) {
            appState.user = data.user;
            localStorage.setItem('user', JSON.stringify(data.user));
            
            showUserInfo();
            fetchLocations();
            showHomeScreen();
            
            // Clear form
            loginForm.reset();
        } else {
            showError('Login failed');
        }
    } catch (error) {
        showError(error.message || 'Login failed');
    }
}

function showUserInfo() {
    if (appState.user) {
        usernameSpan.textContent = appState.user.username;
        userInfo.classList.remove('d-none');
    } else {
        userInfo.classList.add('d-none');
    }
}

function showError(message) {
    loginError.textContent = message;
    loginError.classList.remove('d-none');
}

async function handleLogout() {
    try {
        await apiRequest('/logout', 'POST');
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Clear state regardless of API success
        appState.user = null;
        localStorage.removeItem('user');
        
        // Reset UI
        userInfo.classList.add('d-none');
        showLoginScreen();
    }
}

// Data functions
async function fetchLocations() {
    try {
        const data = await apiRequest('/locations');
        
        appState.locations = data.locations;
        
        // Populate location dropdown
        locationSelect.innerHTML = '';
        
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Select a location';
        locationSelect.appendChild(defaultOption);
        
        appState.locations.forEach(location => {
            const option = document.createElement('option');
            option.value = location.id;
            option.textContent = location.name;
            locationSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error fetching locations:', error);
        // Show error notification
        showNotification('Error loading locations', 'error');
    }
}

function handleLocationChange() {
    const locationId = locationSelect.value;
    
    if (locationId) {
        appState.selectedLocation = appState.locations.find(
            loc => loc.id.toString() === locationId
        );
        console.log('Selected location:', appState.selectedLocation);
    } else {
        appState.selectedLocation = null;
    }
}

// Camera and scanning functions
async function scanQRCode() {
    if (!isNative) {
        // Fallback for web testing - simulate a scan
        const testCodes = ['P123-5', 'C456'];
        return testCodes[Math.floor(Math.random() * testCodes.length)];
    }
    
    try {
        if (Capacitor.isPluginAvailable('Camera')) {
            const { Camera } = Capacitor.Plugins;
            
            // Request camera permission
            const permissionStatus = await Camera.requestPermissions();
            
            if (permissionStatus.camera === 'granted') {
                // Open camera with QR code scanner
                const image = await Camera.getPhoto({
                    quality: 90,
                    allowEditing: false,
                    resultType: 'text',
                    source: 'CAMERA',
                    direction: 'REAR'
                });
                
                if (image.text) {
                    return image.text;
                } else {
                    throw new Error('No QR code detected');
                }
            } else {
                throw new Error('Camera permission denied');
            }
        } else {
            throw new Error('Camera not available');
        }
    } catch (error) {
        console.error('Error scanning QR code:', error);
        throw error;
    }
}

async function scanParentQR() {
    if (!appState.selectedLocation) {
        showNotification('Please select a location first', 'warning');
        return;
    }
    
    try {
        showNotification('Scanning parent bag...', 'info');
        
        const qrCode = await scanQRCode();
        
        // Validate parent QR format (P123-5)
        if (!qrCode.match(/^P\d+-\d+$/)) {
            showNotification('Invalid parent bag QR code format', 'error');
            return;
        }
        
        // Send to API
        const result = await apiRequest('/scan/parent', 'POST', {
            qr_id: qrCode,
            location_id: appState.selectedLocation.id,
            user_id: appState.user.id,
            notes: 'Scanned from mobile app'
        });
        
        // Store current parent bag for child scanning
        appState.currentParentBag = {
            qr_id: qrCode,
            task_id: result.task_id,
            child_count: result.child_count
        };
        
        // Show success
        scanResult.innerHTML = `
            <div class="alert alert-success">
                <h4>Parent Bag Scanned Successfully!</h4>
                <p>QR Code: ${qrCode}</p>
                <p>Expected Child Bags: ${result.child_count}</p>
                <p>Location: ${appState.selectedLocation.name}</p>
            </div>
        `;
        
        showScanResultScreen();
        
    } catch (error) {
        showNotification(error.message || 'Scan failed', 'error');
    }
}

async function scanChildQR() {
    if (!appState.selectedLocation) {
        showNotification('Please select a location first', 'warning');
        return;
    }
    
    if (!appState.currentParentBag) {
        showNotification('Please scan a parent bag first', 'warning');
        return;
    }
    
    try {
        showNotification('Scanning child bag...', 'info');
        
        const qrCode = await scanQRCode();
        
        // Validate child QR format (C123)
        if (!qrCode.match(/^C\d+$/)) {
            showNotification('Invalid child bag QR code format', 'error');
            return;
        }
        
        // Send to API
        const parentBagId = appState.currentParentBag.parent_id || 0;
        
        const result = await apiRequest('/scan/child', 'POST', {
            qr_id: qrCode,
            parent_id: parentBagId,
            location_id: appState.selectedLocation.id,
            user_id: appState.user.id,
            notes: 'Scanned from mobile app'
        });
        
        // Show success
        scanResult.innerHTML = `
            <div class="alert alert-success">
                <h4>Child Bag Scanned Successfully!</h4>
                <p>QR Code: ${qrCode}</p>
                <p>Parent Bag: ${appState.currentParentBag.qr_id}</p>
                <p>Location: ${appState.selectedLocation.name}</p>
            </div>
        `;
        
        showScanResultScreen();
        
    } catch (error) {
        showNotification(error.message || 'Scan failed', 'error');
    }
}

// UI helpers
function showNotification(message, type = 'success') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'success-notification';
    notification.textContent = message;
    
    // Adjust styling based on notification type
    if (type === 'error') {
        notification.style.backgroundColor = 'rgba(220, 53, 69, 0.9)';
    } else if (type === 'warning') {
        notification.style.backgroundColor = 'rgba(255, 193, 7, 0.9)';
        notification.style.color = '#343a40';
    } else if (type === 'info') {
        notification.style.backgroundColor = 'rgba(13, 110, 253, 0.9)';
    }
    
    // Add to body
    document.body.appendChild(notification);
    
    // Trigger animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Remove after timeout
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}