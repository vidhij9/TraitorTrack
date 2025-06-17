# TraceTrack Deployment Guide

This guide provides detailed instructions for deploying the TraceTrack application to production environments.

## Web Application Deployment

### Using Replit Deployment

1. **Prepare Environment Variables**
   
   The following environment variables are required:
   - `DATABASE_URL`: PostgreSQL connection string
   - `SESSION_SECRET`: Secret key for session management
   - `MOBILE_API_KEY`: API key for mobile app authentication

2. **Deploy the Application**
   
   Click the "Deploy" button in the Replit interface to start the deployment process.
   
   Replit will:
   - Build the application
   - Configure the environment
   - Assign a public URL

3. **Post-Deployment Setup**
   
   After deployment, perform these additional steps:
   - Create initial admin user
   - Set up required locations
   - Test the deployed application

### Alternative Deployment Methods

#### Heroku Deployment

```bash
heroku create tracetrack
heroku config:set DATABASE_URL=your_database_url
heroku config:set SESSION_SECRET=your_session_secret
heroku config:set MOBILE_API_KEY=your_mobile_api_key
git push heroku main
```

#### Docker Deployment

```bash
docker build -t tracetrack .
docker run -p 5000:5000 \
  -e DATABASE_URL=your_database_url \
  -e SESSION_SECRET=your_session_secret \
  -e MOBILE_API_KEY=your_mobile_api_key \
  tracetrack
```

## Android App Deployment

The TraceTrack Android app can be built and distributed through various channels.

### Building the APK

1. **Update API Configuration**
   
   In `mobile/app.js`, update the `API_BASE_URL` variable to point to your deployed web application:
   
   ```javascript
   const API_BASE_URL = 'https://your-deployed-domain.replit.app/mobile-api';
   ```

2. **Run the Build Script**
   
   ```bash
   cd mobile
   ./build-android.sh
   ```

3. **Open in Android Studio**
   
   ```bash
   npx cap open android
   ```

4. **Generate Signed APK**
   
   In Android Studio:
   - Select `Build > Generate Signed Bundle/APK`
   - Follow the instructions to create or select a signing key
   - Choose APK as the build type
   - Select release build variant
   - Click Finish to generate the APK

### Distribution Options

1. **Google Play Store**
   - Create a Google Play Developer account
   - Create a new application in the Google Play Console
   - Upload the signed APK
   - Complete the store listing information
   - Submit for review

2. **Direct Distribution**
   - Host the APK on your website
   - Share the direct download link with users
   - Provide instructions for enabling "Unknown Sources" installation

## Database Migration

When deploying updates that include database schema changes:

1. **Test Migrations Locally**
   ```bash
   flask db upgrade
   ```

2. **Apply Migrations During Deployment**
   Ensure that migration scripts run as part of the deployment process.

3. **Backup Before Migrating**
   Always create a database backup before running migrations in production.

## Performance Monitoring

Monitor the deployed application using:

- System Status API: `/api/system`
- Entity Counts API: `/api/entity-counts` 
- Activity Stats API: `/api/activity/{days}`
- Cache Statistics API: `/api/cache/stats`

## Security Considerations

1. **API Keys**
   - Rotate the mobile API key periodically
   - Use environment variables for all secrets, never hardcode

2. **Database Access**
   - Restrict database access to application IP addresses
   - Use TLS for database connections

3. **Authentication**
   - Enforce strong password policies
   - Implement rate limiting for login attempts

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify DATABASE_URL is correctly formatted
   - Check network rules to ensure the application can reach the database

2. **Mobile API Issues**
   - Verify the correct API key is configured
   - Ensure the mobile API endpoints are accessible from public networks

3. **Performance Issues**
   - Monitor cache hit rates via `/api/cache/stats`
   - Check database query performance
   - Verify asynchronous tasks are processing correctly

For further assistance, contact the development team.
