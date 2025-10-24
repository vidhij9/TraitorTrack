# TraceTrack Testing Documentation

## Test Suite Overview

TraceTrack includes a comprehensive testing suite covering unit tests, integration tests, and load testing.

## Running Tests

### Unit and Integration Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test class
pytest tests/test_models.py::TestUserModel -v
```

### Test Structure

- **tests/conftest.py**: Pytest fixtures for database, users, bags, and bills
- **tests/test_models.py**: Unit tests for User, Bag, Bill models
- **tests/test_auth.py**: Integration tests for authentication and authorization
- **tests/test_bags.py**: Integration tests for bag management and scanning
- **tests/test_bills.py**: Integration tests for bill creation and management

### Test Fixtures

The test suite provides fixtures for:
- Database session (automatically rolled back after each test)
- Admin, biller, and dispatcher users
- Parent and child bags with relationships
- Bills and bill-bag associations
- Authenticated test client

## Load Testing

### Using Locust for Load Testing

Load testing simulates multiple concurrent users to verify performance under stress.

```bash
# Start Locust web interface
locust -f locustfile.py --host=http://localhost:5000

# Run headless load test (50 users, 5 users/second spawn rate)
locust -f locustfile.py --host=http://localhost:5000 --users 50 --spawn-rate 5 --run-time 2m --headless

# Run intensive load test (100+ users)
locust -f locustfile.py --host=http://localhost:5000 --users 100 --spawn-rate 10 --run-time 5m --headless
```

### Load Test Scenarios

**TraceTrackUser** (70% of traffic):
- View dashboard (high frequency)
- Browse bag management
- Browse bill management
- Access scanning pages
- View reports
- API health checks

**HeavyLoadUser** (30% of traffic):
- Create new bills
- Process parent bag scans
- Heavy database operations

### Performance Targets

- **Dashboard load**: < 100ms response time
- **Bag/bill management**: < 200ms response time
- **Scanning operations**: < 150ms response time
- **Concurrent users**: Support 100+ simultaneous users
- **Database connections**: Efficient pool usage (20 base + 10 overflow)

### Interpreting Load Test Results

Monitor these metrics in Locust:
1. **Requests/second (RPS)**: Should maintain steady rate
2. **Response times (50th, 95th, 99th percentile)**: Should stay under targets
3. **Failure rate**: Should be < 1%
4. **Connection pool**: Check logs for pool exhaustion

## End-to-End Testing

End-to-end tests using Playwright verify complete user workflows.

### Critical Workflows to Test

1. **Authentication Flow**
   - User registration
   - Login/logout
   - Role-based access control

2. **Bag Management Flow**
   - Create parent bag
   - Scan child bags
   - Link child to parent
   - View bag details

3. **Bill Management Flow**
   - Create new bill
   - Scan parent bags for bill
   - Link bags to bill
   - Complete bill
   - Generate reports

4. **Excel Upload Flow**
   - Upload Excel file with bags
   - Validate data
   - Create bags in bulk
   - Handle errors

### Running E2E Tests

Use the `run_test` tool to execute playwright-based end-to-end tests for browser interactions.

## Test Coverage Goals

- **Models**: 90%+ coverage
- **Routes**: 80%+ coverage
- **Critical paths**: 100% coverage
- **Edge cases**: Comprehensive error handling

## Continuous Testing

Run tests before:
- Committing changes
- Deploying to production
- Major refactors

Run load tests:
- Before production deployment
- After performance optimization
- Monthly performance validation

## Test Data

Tests use isolated SQLite in-memory database to ensure:
- Fast execution
- No interference with development data
- Clean state for each test
- Parallel test execution

## Known Test Limitations

1. Template-based tests may fail without full context setup
2. Some integration tests require specific session state
3. Load tests require actual database with realistic data volume

## Future Testing Improvements

1. Add more comprehensive Excel upload tests
2. Test concurrent scanning scenarios
3. Add performance regression tests
4. Implement automated e2e test suite
5. Add API endpoint tests for mobile integration
