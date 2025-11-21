.PHONY: test test-unit test-integration test-security test-all test-fast coverage help load-test stress-test db-scale-test

# Default target
help:
        @echo "TraitorTrack Test Commands"
        @echo "=========================="
        @echo ""
        @echo "Backend Tests:"
        @echo "  make test         - Run all tests (recommended before publishing)"
        @echo "  make test-unit    - Run only unit tests (fast)"
        @echo "  make test-integration - Run integration tests"
        @echo "  make test-security    - Run security tests"
        @echo "  make test-fast    - Run all tests except slow ones"
        @echo "  make coverage     - Run tests with coverage report"
        @echo ""
        @echo "Load & Performance Tests:"
        @echo "  make load-test    - Run Locust load tests (100+ concurrent users)"
        @echo "  make stress-test  - Run stress tests to find breaking points"
        @echo "  make db-scale-test - Test database performance at scale"
        @echo "  make api-perf     - Test API endpoint performance"
        @echo ""
        @echo "  make help         - Show this help message"
        @echo ""

# Run all tests - THIS IS YOUR PRE-PUBLISH COMMAND
test:
        @echo "🧪 Running comprehensive test suite..."
        @./run_tests.sh

# Run only unit tests (fast)
test-unit:
        @echo "🧪 Running unit tests only..."
        @TESTING=True FORCE_DEV_DB=1 pytest -m unit -v

# Run integration tests
test-integration:
        @echo "🧪 Running integration tests..."
        @TESTING=True FORCE_DEV_DB=1 pytest -m integration -v

# Run security tests
test-security:
        @echo "🧪 Running security tests..."
        @TESTING=True FORCE_DEV_DB=1 pytest -m security -v

# Run all tests except slow ones
test-fast:
        @echo "🧪 Running fast tests only..."
        @./run_tests.sh --fast

# Run tests with coverage report
coverage:
        @echo "🧪 Running tests with coverage..."
        @./run_tests.sh --coverage
        @echo ""
        @echo "📊 Coverage report generated in htmlcov/index.html"

# Quick smoke test
smoke:
        @echo "🧪 Running quick smoke test..."
        @TESTING=True FORCE_DEV_DB=1 pytest tests/test_auth.py::TestAuthentication::test_login_page_loads -v

# Load testing - requires running server
load-test:
        @echo "🔥 Starting load test (100 concurrent users)..."
        @echo "⚠️  Make sure server is running: make run (or gunicorn)"
        @echo ""
        @locust -f tests/load/locustfile.py --host=http://localhost:5000 --headless -u 100 -r 10 -t 5m

# Stress testing - find breaking points
stress-test:
        @echo "💪 Starting stress test (200 concurrent users)..."
        @echo "⚠️  Make sure server is running: make run (or gunicorn)"
        @echo ""
        @locust -f tests/load/stress_test.py --host=http://localhost:5000 --headless -u 200 -r 20 -t 10m

# Database scale testing
db-scale-test:
        @echo "📊 Testing database performance at scale..."
        @python tests/load/db_scale_test.py

# API performance testing
api-perf:
        @echo "⚡ Testing API endpoint performance..."
        @echo "⚠️  Make sure server is running: make run (or gunicorn)"
        @echo ""
        @locust -f tests/load/locustfile.py --host=http://localhost:5000 --headless -u 50 -r 10 -t 3m --tags api-perf

# Interactive load test (Web UI)
load-test-ui:
        @echo "🌐 Starting Locust Web UI..."
        @echo "⚠️  Make sure server is running: make run (or gunicorn)"
        @echo "📊 Visit http://localhost:8089 to control the test"
        @echo ""
        @locust -f tests/load/locustfile.py --host=http://localhost:5000
