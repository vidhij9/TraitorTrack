# TraceTrack - Supply Chain Traceability Platform

## Overview
A cutting-edge supply chain traceability platform leveraging digital technologies to streamline agricultural bag tracking and management.

## Key Features
- Flask web framework with Python backend
- JWT-based stateless authentication  
- Mobile-first responsive design
- JavaScript-powered QR code scanning
- Role-based access control
- Real-time data tracking and analytics
- Comprehensive error logging and debugging

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python main.py

# Access at http://localhost:5000
# Default login: admin/admin
```

## File Structure
```
├── main.py              # Application entry point
├── app_clean.py         # Flask application configuration
├── routes.py            # URL routes and handlers
├── models.py            # Database models
├── forms.py             # Form definitions
├── templates/           # HTML templates
├── static/              # CSS, JS, images
└── mobile/              # Mobile app components
```

## API Endpoints
- `/api/stats` - System statistics
- `/api/scans` - Recent scan data
- `/api/bags/parent/list` - Parent bag listing
- `/api/bags/child/list` - Child bag listing

## Deployment
Use Replit deployment or configure with:
```bash
gunicorn --bind 0.0.0.0:5000 main:app
```

## Database
PostgreSQL with automatic table creation and optimization.

## Security
- CSRF protection on all forms
- Account lockout protection
- Session-based authentication
- Input validation and sanitization
