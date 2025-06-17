# TraceTrack API Documentation

## Overview
The TraceTrack API has been improved with more descriptive, functionality-based endpoint names that clearly indicate their purpose and capabilities.

## API Structure

### 1. Bag Management Endpoints

#### Get All Parent Bags
- **New Endpoint**: `GET /api/bags/parent/list`
- **Old Endpoint**: `GET /api/parent_bags` (deprecated)
- **Description**: Retrieve complete list of all parent bags in the system
- **Response**:
```json
{
  "success": true,
  "data": [...],
  "count": 15,
  "timestamp": 1234567890,
  "cached": false
}
```

#### Get All Child Bags
- **New Endpoint**: `GET /api/bags/child/list`
- **Old Endpoint**: `GET /api/child_bags` (deprecated)
- **Description**: Retrieve complete list of all child bags in the system

#### Get Parent Bag Details
- **New Endpoint**: `GET /api/bags/parent/{qr_id}/details`
- **Old Endpoint**: `GET /api/parent_bag/{qr_id}` (deprecated)
- **Description**: Get detailed information about a specific parent bag including its children
- **Response**:
```json
{
  "success": true,
  "data": {
    "parent_bag": {...},
    "child_bags": [...],
    "child_count": 5,
    "expected_child_count": 5
  }
}
```

#### Get Child Bag Details
- **New Endpoint**: `GET /api/bags/child/{qr_id}/details`
- **Old Endpoint**: `GET /api/child_bag/{qr_id}` (deprecated)
- **Description**: Get detailed information about a specific child bag including its parent
- **Response**:
```json
{
  "success": true,
  "data": {
    "child_bag": {...},
    "parent_bag": {...},
    "is_linked": true
  }
}
```

### 2. Scan Tracking Endpoints

#### Get Parent Bag Scan History
- **New Endpoint**: `GET /api/tracking/parent/{qr_id}/scan-history`
- **Old Endpoint**: `GET /api/parent_bag/{qr_id}/scans` (deprecated)
- **Description**: Get complete scan history for a parent bag
- **Response**:
```json
{
  "success": true,
  "data": {
    "parent_bag": {...},
    "scan_history": [...],
    "total_scans": 25,
    "last_scan": {...}
  }
}
```

#### Get Child Bag Scan History
- **New Endpoint**: `GET /api/tracking/child/{qr_id}/scan-history`
- **Old Endpoint**: `GET /api/child_bag/{qr_id}/scans` (deprecated)
- **Description**: Get complete scan history for a child bag

#### Get Recent Scan Activity
- **New Endpoint**: `GET /api/tracking/scans/recent`
- **Old Endpoint**: `GET /api/scans` (deprecated)
- **Description**: Get recent scan activity across the entire system with filtering options
- **Query Parameters**:
  - `limit` (int): Number of records to return (default: 50)
  - `type` (string): 'parent' or 'child' to filter by scan type
  - `user_id` (int): Filter by specific user
  - `days` (int): Filter by number of days back
- **Response**:
```json
{
  "success": true,
  "data": {
    "scans": [...],
    "count": 25,
    "filters_applied": {
      "type": "parent",
      "user_id": null,
      "days": 7,
      "limit": 50
    }
  }
}
```

### 3. Analytics & Statistics Endpoints

#### Get System Analytics Overview
- **New Endpoint**: `GET /api/analytics/system-overview`
- **Old Endpoint**: `GET /api/stats` (deprecated)
- **Description**: Get comprehensive system statistics and analytics overview
- **Response**:
```json
{
  "success": true,
  "data": {
    "totals": {
      "parent_bags": 15,
      "child_bags": 75,
      "total_bags": 90,
      "total_scans": 250,
      "total_users": 5
    },
    "scan_breakdown": {
      "parent_scans": 100,
      "child_scans": 150
    },
    "recent_activity": {
      "scans_last_7_days": 45,
      "active_users_last_7_days": 3
    },
    "generated_at": "2025-06-16T06:56:45.123456"
  }
}
```

### 4. System Management Endpoints

#### Get Cache System Status
- **New Endpoint**: `GET /api/system/cache/status`
- **Old Endpoint**: `GET /api/cache_stats` (deprecated)
- **Description**: Get detailed cache system performance statistics
- **Response**:
```json
{
  "success": true,
  "data": {
    "cache_performance": {...},
    "cache_health": "healthy"
  }
}
```

#### Clear System Cache
- **New Endpoint**: `POST /api/system/cache/clear`
- **Old Endpoint**: `POST /api/clear_cache` (deprecated)
- **Description**: Clear application cache with optional prefix targeting
- **Request Body**:
```json
{
  "prefix": "bags_"  // Optional: target specific cache entries
}
```
- **Response**:
```json
{
  "success": true,
  "message": "Cache with prefix bags_ cleared",
  "cleared_scope": "bags_"
}
```

#### System Health Check
- **New Endpoint**: `GET /api/system/health-check`
- **Description**: Comprehensive system health check endpoint
- **Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-16T06:56:45.123456",
  "checks": {
    "database": "connected",
    "recent_activity": "45 scans in last 24 hours"
  },
  "version": "2.0.0"
}
```

### 5. Development & Testing Endpoints

#### Create Sample Data
- **New Endpoint**: `POST /api/development/seed-sample-data`
- **Old Endpoint**: `POST /api/seed_test_data` (deprecated)
- **Description**: Create sample data for development and testing
- **Response**:
```json
{
  "success": true,
  "message": "Sample data created successfully",
  "data": {
    "parent_bags_created": ["SAMPLE-P101", "SAMPLE-P102", "SAMPLE-P103"],
    "child_bags_created": ["SAMPLE-C101-1", "SAMPLE-C101-2", ...],
    "scans_created": 15,
    "relationships_established": 15
  }
}
```

## API Improvements Summary

### 1. Descriptive Naming
- **Before**: `/api/parent_bags` 
- **After**: `/api/bags/parent/list`
- **Benefit**: Clearly indicates this retrieves a list of parent bags

### 2. Hierarchical Structure
- **Bag Management**: `/api/bags/...`
- **Tracking**: `/api/tracking/...`
- **Analytics**: `/api/analytics/...`
- **System Management**: `/api/system/...`
- **Development**: `/api/development/...`

### 3. Action-Oriented Endpoints
- **Before**: `/api/parent_bag/{id}/scans`
- **After**: `/api/tracking/parent/{id}/scan-history`
- **Benefit**: Emphasizes the tracking functionality and historical data retrieval

### 4. Enhanced Response Structure
- Consistent `success` indicator
- Structured `data` wrapper
- Additional metadata (counts, timestamps, health indicators)
- Clear error codes for better debugging

### 5. Backward Compatibility
- All old endpoints remain functional
- Deprecation warnings logged for migration planning
- Gradual migration path without breaking existing integrations

## Error Handling

### Standard Error Response Format
```json
{
  "success": false,
  "error": "Resource not found",
  "error_code": "PARENT_BAG_NOT_FOUND"
}
```

### HTTP Status Codes
- `200 OK`: Successful request
- `404 Not Found`: Resource not found
- `403 Forbidden`: Insufficient privileges
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: System health issues

## Authentication
All endpoints require authentication except:
- `GET /api/system/health-check`

Include authentication headers with all API requests.

## Migration Guide

### Step 1: Update API Calls
Replace old endpoint URLs with new descriptive ones:
```javascript
// Old
fetch('/api/parent_bags')

// New
fetch('/api/bags/parent/list')
```

### Step 2: Update Response Handling
Adapt to new response structure:
```javascript
// Old response structure
response.parent_bags

// New response structure
response.data
```

### Step 3: Leverage Enhanced Features
Use new filtering and metadata capabilities:
```javascript
// Enhanced filtering
fetch('/api/tracking/scans/recent?type=parent&days=7&limit=20')

// Access metadata
console.log(`Total items: ${response.count}`);
console.log(`Cache health: ${response.data.cache_health}`);
```

This improved API structure provides better functionality understanding, enhanced features, and maintains backward compatibility for seamless migration.
