# TraceTrack - Supply Chain Tracking System

A high-performance web and mobile application for comprehensive traceability tracking of agricultural products through the supply chain.

## Features

- QR code-based tracking system for parent and child bags
- Cross-platform web and mobile interfaces
- Real-time data synchronization
- Offline capabilities with background sync
- Comprehensive reporting and analytics
- Role-based access control (employee/admin)

## Performance Optimizations

TraceTrack includes advanced performance optimizations that make it faster and more reliable than commercial solutions like Kezzler:

1. **Tiered Caching System**
   - Memory cache for fast access to frequent data
   - Disk persistence for larger datasets
   - Namespace support for targeted cache invalidation

2. **Asynchronous Processing**
   - Background task queue for scan operations
   - Real-time UI updates while processing continues in background
   - Task status monitoring and recovery

3. **Database Optimizations**
   - Strategic indexing on frequently queried fields
   - Connection pooling for high concurrency
   - Query optimization with eager loading

4. **Mobile App Integration**
   - Native camera access for QR scanning
   - Offline-first architecture
   - Background synchronization

## Web Application Deployment

### Prerequisites

- Python 3.11+
- PostgreSQL database
- Node.js 20+ (for mobile app development)

### Deployment Steps

1. Clone the repository:
   ```
   git clone <repository-url>
   cd tracetrack
   ```

2. Set up environment variables:
   ```
   export DATABASE_URL=postgresql://user:password@localhost/tracetrack
   export SESSION_SECRET=your-secret-key
   export ADMIN_PASSWORD=your-admin-password
   export MOBILE_API_KEY=your-mobile-api-key
   ```
   `SESSION_SECRET` **must** be set to a strong random value before starting the application.

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```
   flask db upgrade
   ```

5. Start the application:
   ```
   gunicorn --bind 0.0.0.0:5000 main:app
   ```

The application will be available at `http://localhost:5000`

## Mobile App Development

### Prerequisites

- Node.js 20+
- Android Studio (for Android builds)
- Xcode (for iOS builds, Mac only)

### Building the Android App

1. Navigate to the mobile directory:
   ```
   cd mobile
   ```

2. Install Capacitor dependencies:
   ```
   npm install @capacitor/core @capacitor/cli @capacitor/android @capacitor/camera
   ```

3. Update the API URL in `app.js` to your deployed web application URL

4. Run the build script:
   ```
   ./build-android.sh
   ```

5. Open Android Studio to build the APK:
   ```
   npx cap open android
   ```

6. In Android Studio, select `Build > Build Bundle(s) / APK(s) > Build APK(s)`

### Customizing the Mobile App

- Update `styles.css` to customize the look and feel
- Edit `index.html` to change the UI structure
- Modify `app.js` to add new functionality

## API Documentation

TraceTrack provides a comprehensive API for integration with other systems:

- Web API: `/api/*` endpoints for web interface
- Mobile API: `/mobile-api/*` endpoints optimized for mobile

See the [API Documentation](docs/api.md) for details on available endpoints.

## System Monitoring

TraceTrack includes built-in health and performance monitoring:

- System Status: `/api/system`
- Entity Counts: `/api/entity-counts`
- Activity Stats: `/api/activity/{days}`
- Cache Statistics: `/api/cache/stats`
- Task Queue Stats: Available on the admin dashboard

## License

[MIT](LICENSE)

## Acknowledgements

- Inspired by the need for better supply chain traceability systems
- Special thanks to all contributors
