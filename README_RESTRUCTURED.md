# TraceTrack - Restructured Codebase

## Overview

This document describes the restructured TraceTrack application with improved code organization, better separation of concerns, and enhanced maintainability.

## New Directory Structure

```
├── src/                          # Main source code directory
│   ├── __init__.py              # Package initialization
│   ├── core/                    # Core application components
│   │   ├── __init__.py
│   │   └── app.py              # Application factory and configuration
│   ├── models/                  # Database models (organized by entity)
│   │   ├── __init__.py
│   │   ├── user.py             # User model and roles
│   │   ├── bag.py              # Bag models and types
│   │   ├── scan.py             # Scan tracking model
│   │   ├── bill.py             # Billing models
│   │   ├── link.py             # Parent-child bag relationships
│   │   └── role.py             # Role and permission models
│   ├── auth/                    # Authentication system
│   │   ├── __init__.py
│   │   └── auth.py             # Consolidated authentication logic
│   └── utils/                   # Utility modules
│       ├── __init__.py
│       ├── cache.py            # Caching utilities
│       ├── validation.py       # Input validation
│       └── database.py         # Database utilities
├── app_restructured.py          # Main application entry point
├── config_restructured.py       # Unified configuration
├── templates/                   # HTML templates (unchanged)
├── static/                      # Static assets (unchanged)
└── README_RESTRUCTURED.md       # This documentation
```

## Key Improvements

### 1. **Modular Architecture**
- **Separation of Concerns**: Each module has a single responsibility
- **Clean Dependencies**: Clear import hierarchy with minimal circular dependencies
- **Reusable Components**: Utilities and core components can be easily reused

### 2. **Organized Models**
- **Entity-Based Organization**: Each model type in its own file
- **Clear Relationships**: Well-defined relationships between entities
- **Consistent Structure**: Standardized model definitions with proper indexing

### 3. **Consolidated Authentication**
- **Single Auth System**: One unified authentication module instead of multiple scattered implementations
- **Security Features**: Account lockout, token management, and secure session handling
- **Decorator Support**: Easy-to-use decorators for protecting routes

### 4. **Improved Configuration**
- **Environment-Specific**: Different configurations for development, production, and testing
- **Centralized Settings**: All configuration in one place
- **Environment Variables**: Proper use of environment variables for sensitive data

### 5. **Better Error Handling**
- **Centralized Error Handlers**: Consistent error responses
- **Logging Integration**: Comprehensive logging throughout the application
- **Health Checks**: Built-in health monitoring endpoints

## Usage

### Running the Restructured Application

1. **Use the new entry point:**
   ```python
   # Instead of app_clean.py, use:
   python app_restructured.py
   ```

2. **Or import the application:**
   ```python
   from app_restructured import app
   # Use with gunicorn or other WSGI servers
   ```

### Key Components

#### **Authentication System**
```python
from src.auth.auth import login_user, require_auth, require_admin

# Login a user
success, message, user_data = login_user(username, password)

# Protect routes
@require_auth
def protected_route():
    pass

@require_admin  
def admin_only_route():
    pass
```

#### **Database Models**
```python
from src.models import User, Bag, Scan, Bill, Link

# Create a new user
user = User(username='john', email='john@example.com')
user.set_password('password123')

# Create a bag
bag = Bag(qr_id='BAG001', type='parent', name='Sample Bag')

# Record a scan
scan = Scan(qr_code='BAG001', user_id=user.id)
```

#### **Caching**
```python
from src.utils.cache import cached, get_cache_stats

@cached(timeout=300)  # 5 minutes
def expensive_operation():
    return complex_calculation()

# Get cache statistics
stats = get_cache_stats()
```

#### **Validation**
```python
from src.utils.validation import validate_qr_code, validate_email

# Validate inputs
valid, message = validate_qr_code('BAG001')
valid, message = validate_email('user@example.com')
```

## Migration from Old Structure

### **Files Replaced**
- `app_clean.py` → `app_restructured.py`
- `models.py` → `src/models/*.py`
- Multiple auth files → `src/auth/auth.py`
- `config.py` → `config_restructured.py`

### **Import Changes**
```python
# Old imports
from models import User, Bag
from simple_auth import login_user

# New imports  
from src.models import User, Bag
from src.auth.auth import login_user
```

### **Configuration Changes**
```python
# Old way
from config import Config

# New way
from config_restructured import get_config
config = get_config()
```

## Benefits of Restructuring

### **For Developers**
- **Easier Navigation**: Clear directory structure makes finding code intuitive
- **Reduced Complexity**: Smaller, focused files are easier to understand and modify
- **Better Testing**: Modular structure enables better unit testing
- **Consistent Patterns**: Standardized approaches across all modules

### **For Maintenance**
- **Isolated Changes**: Modifications to one feature don't affect others
- **Clear Dependencies**: Easy to understand what depends on what
- **Documentation**: Self-documenting code structure
- **Debugging**: Easier to trace issues through the organized codebase

### **For Deployment**
- **Environment Management**: Clear separation of configuration for different environments
- **Health Monitoring**: Built-in health checks and monitoring
- **Security**: Improved security practices throughout the application
- **Performance**: Better caching and database connection management

## API Compatibility

The restructured application maintains **full API compatibility** with the existing system:

- All existing routes work unchanged
- Database schema remains identical  
- External integrations continue to function
- Mobile app compatibility preserved

## Next Steps

1. **Test the restructured application** thoroughly
2. **Update deployment scripts** to use the new entry point
3. **Train team members** on the new structure
4. **Gradually migrate** custom modifications to the new structure
5. **Remove old files** once migration is complete

## Support

The restructured codebase maintains all existing functionality while providing a much cleaner and more maintainable foundation for future development.
