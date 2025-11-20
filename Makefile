.PHONY: test test-unit test-integration test-security test-all test-fast coverage help

# Default target
help:
	@echo "TraitorTrack Test Commands"
	@echo "=========================="
	@echo ""
	@echo "  make test         - Run all tests (recommended before publishing)"
	@echo "  make test-unit    - Run only unit tests (fast)"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-security    - Run security tests"
	@echo "  make test-fast    - Run all tests except slow ones"
	@echo "  make coverage     - Run tests with coverage report"
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
