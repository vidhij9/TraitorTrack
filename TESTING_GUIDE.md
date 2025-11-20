# Testing Guide for TraitorTrack

## Quick Start - Pre-Publishing Command

**Before publishing, run this single command:**

```bash
make test
```

or

```bash
./run_tests.sh
```

This runs all test suites and ensures your application is ready for production.

---

## Test Organization

Tests are organized into categories using pytest markers:

- **Unit Tests** (`@pytest.mark.unit`) - Fast tests, no database
- **Integration Tests** (`@pytest.mark.integration`) - Tests with database
- **Security Tests** (`@pytest.mark.security`) - SQL injection, XSS, CSRF
- **Race Condition Tests** (`@pytest.mark.race`) - Concurrent operations
- **Unicode Tests** (`@pytest.mark.unicode`) - Unicode and special characters
- **E2E Tests** - End-to-end Playwright tests

---

## Test Coverage Breakdown

### Backend Tests (Pytest)

**Unit Tests** (`tests/test_models.py`)
- User model creation and validation
- Bag model (parent/child)
- Bill model
- Relationships and constraints

**Integration Tests**
- `tests/test_auth.py` - Authentication (login, logout, registration, roles)
- `tests/test_bags.py` - Bag management (scanning, linking, search)
- `tests/test_bills.py` - Bill operations (create, finalize, link bags)

**Security Tests** (`tests/test_security.py`)
- TC-099: SQL injection prevention
- TC-099: XSS prevention
- CSRF protection
- Input sanitization

**Race Condition Tests** (`tests/test_race_conditions.py`)
- TC-094: Simultaneous bag scan prevention
- TC-095: Simultaneous user deletion
- TC-096: Simultaneous bill finalization
- TC-106: Atomic parent bag duplicate prevention
- TC-105: Concurrent cache invalidation

**Unicode Tests** (`tests/test_unicode.py`)
- TC-097: Unicode rejection in QR codes (ASCII-only)
- TC-098: Unicode support in customer names
- TC-104: CSV export/import with Unicode

**Error Recovery Tests** (`tests/test_error_recovery.py`)
- TC-100: Transaction rollback on errors
- TC-101: Partial CSV import failures
- TC-102: Cache invalidation after errors
- TC-103: Undo time window enforcement (1 hour)
- TC-107: Session timeout handling
- TC-108: Foreign key constraint enforcement

### Frontend Tests (Playwright)

**E2E Tests**
- `test_critical_flows.py` - Critical user workflows
- `test_mobile_viewport.py` - Mobile responsiveness
- `test_mobile_warehouse.py` - Warehouse mode on mobile
- `test_parent_bag_validation.py` - Parent bag validation flows

---

## Running Tests

### Run All Tests (Recommended)
```bash
make test
# or
./run_tests.sh
```

### Run Specific Test Categories
```bash
# Unit tests only (fast)
make test-unit

# Integration tests
make test-integration

# Security tests
make test-security

# Fast tests (skip slow ones)
make test-fast
```

### Run Tests with Coverage
```bash
make coverage
# Opens coverage report in htmlcov/index.html
```

### Run Single Test File
```bash
pytest tests/test_auth.py -v
```

### Run Single Test
```bash
pytest tests/test_auth.py::TestAuthentication::test_login_success -v
```

---

## Database Safety

**CRITICAL:** Tests NEVER run against production database!

Safety mechanisms:
1. **Environment Variables:**
   - `TESTING=True` - Enables test mode
   - `FORCE_DEV_DB=1` - Forces development database

2. **Automatic Checks:**
   - Tests use SQLite in-memory database by default
   - Script verifies no production database strings in DATABASE_URL
   - Fails immediately if production database detected

3. **Production Protection:**
   - All tests use fixtures that create isolated data
   - Each test cleans up after itself
   - No data persists between test runs

---

## Test Results

### Success Output
```
========================================
  TraitorTrack Test Suite
========================================

Safety Checks:
  TESTING=True
  FORCE_DEV_DB=1
  DATABASE_URL=sqlite:///test.db

✓ Safety checks passed - using development database

=== Unit Tests ===
✓ Unit Tests passed

=== Integration Tests ===
✓ Integration Tests passed

=== Security Tests ===
✓ Security Tests passed

========================================
  Test Results Summary
========================================

Test Categories:
  Passed: 6
  Failed: 0

✓ All tests passed!
✓ Ready for publishing
```

### Failure Output
```
✗ Security Tests failed

========================================
  Test Results Summary
========================================

Test Categories:
  Passed: 5
  Failed: 1

✗ 1 test category(ies) failed
✗ Fix failures before publishing
```

---

## Adding New Tests

### 1. Choose Test Type

```python
# Unit test
pytestmark = pytest.mark.unit

# Integration test
pytestmark = pytest.mark.integration

# Security test
pytestmark = [pytest.mark.security, pytest.mark.integration]
```

### 2. Use Fixtures

Available fixtures from `tests/conftest.py`:
- `app` - Flask application
- `client` - Test client
- `db_session` - Database session
- `admin_user`, `biller_user`, `dispatcher_user` - Pre-created users
- `parent_bag`, `child_bags` - Pre-created bags
- `bill` - Pre-created bill
- `authenticated_client` - Logged-in client

### 3. Write Test

```python
import pytest
from models import Bag

pytestmark = pytest.mark.integration

class TestMyFeature:
    def test_create_bag(self, db_session):
        """Test bag creation"""
        bag = Bag()
        bag.qr_id = 'TEST001'
        bag.type = 'parent'
        bag.name = 'Test Bag'
        db_session.add(bag)
        db_session.commit()
        
        assert bag.id is not None
        assert bag.qr_id == 'TEST001'
```

### 4. Run Your Test

```bash
pytest tests/test_my_feature.py -v
```

---

## Coverage Goals

**Target: >80% code coverage**

Check coverage:
```bash
make coverage
open htmlcov/index.html
```

### High Priority Coverage
- [ ] All authentication flows
- [ ] All bag operations (scan, link, delete)
- [ ] All bill operations (create, finalize, delete)
- [ ] Security endpoints
- [ ] Error handling paths

---

## Troubleshooting

### Tests Fail with Database Error
**Solution:** Ensure `FORCE_DEV_DB=1` is set
```bash
export FORCE_DEV_DB=1
export TESTING=True
make test
```

### Import Errors
**Solution:** Ensure you're in the project root directory
```bash
cd /path/to/traitortrack
make test
```

### Playwright Tests Don't Run
**Solution:** Install Playwright browsers
```bash
playwright install chromium
```

### Server Not Starting for E2E Tests
**Solution:** Check if port 5000 is available
```bash
# Kill any process on port 5000
lsof -ti:5000 | xargs kill -9
# Then run tests again
make test
```

---

## CI/CD Integration

For automated testing in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Tests
  run: |
    export TESTING=True
    export FORCE_DEV_DB=1
    make test
```

---

## Test Case Mapping

Tests cover all 108 manual test cases from `TEST_CASES.md`:

- **TC-001 to TC-093:** Covered by existing integration tests
- **TC-094 to TC-096:** Race condition tests
- **TC-097 to TC-099:** Unicode and security tests
- **TC-100 to TC-103:** Error recovery tests
- **TC-104:** CSV export/import tests
- **TC-105:** Concurrent cache tests
- **TC-106:** Atomic operations tests
- **TC-107:** Session timeout tests
- **TC-108:** Foreign key constraint tests

---

## Support

If tests fail:
1. Check error messages in terminal
2. Review test logs
3. Verify database safety variables are set
4. Check that you're not on production environment

**Remember:** Never skip tests before publishing!
