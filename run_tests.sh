#!/bin/bash
#
# Comprehensive Test Runner for TraitorTrack
# Runs all test suites: unit, integration, E2E, security, and generates coverage report
#
# Usage: ./run_tests.sh [options]
#   --unit          Run only unit tests
#   --integration   Run only integration tests
#   --e2e           Run only E2E/Playwright tests
#   --security      Run only security tests
#   --fast          Skip slow tests
#   --coverage      Generate coverage report
#   --help          Show this help message
#

set -e  # Exit on first error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_E2E=true
RUN_SECURITY=true
RUN_SLOW=true
GENERATE_COVERAGE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_INTEGRATION=false
            RUN_E2E=false
            RUN_SECURITY=false
            shift
            ;;
        --integration)
            RUN_UNIT=false
            RUN_E2E=false
            RUN_SECURITY=false
            shift
            ;;
        --e2e)
            RUN_UNIT=false
            RUN_INTEGRATION=false
            RUN_SECURITY=false
            shift
            ;;
        --security)
            RUN_UNIT=false
            RUN_INTEGRATION=false
            RUN_E2E=false
            shift
            ;;
        --fast)
            RUN_SLOW=false
            shift
            ;;
        --coverage)
            GENERATE_COVERAGE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "  --unit          Run only unit tests"
            echo "  --integration   Run only integration tests"
            echo "  --e2e           Run only E2E/Playwright tests"
            echo "  --security      Run only security tests"
            echo "  --fast          Skip slow tests"
            echo "  --coverage      Generate coverage report"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Safety checks
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TraitorTrack Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Ensure we're using development database
export TESTING=True
export FORCE_DEV_DB=1
export DATABASE_URL=${DATABASE_URL:-sqlite:///test.db}

echo -e "${YELLOW}Safety Checks:${NC}"
echo "  TESTING=$TESTING"
echo "  FORCE_DEV_DB=$FORCE_DEV_DB"
echo "  DATABASE_URL=$DATABASE_URL"

# Verify not using production database
if [[ "$DATABASE_URL" == *"traitortrack_prod"* ]] || [[ "$DATABASE_URL" == *"aws"* ]]; then
    echo -e "${RED}ERROR: Production database detected!${NC}"
    echo -e "${RED}Tests must NEVER run against production database.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Safety checks passed - using development database${NC}"
echo ""

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run pytest with markers
run_pytest() {
    local name=$1
    local markers=$2
    local extra_args=$3
    
    echo -e "${BLUE}Running $name...${NC}"
    
    if $GENERATE_COVERAGE; then
        extra_args="$extra_args --cov=. --cov-report=html --cov-report=term"
    fi
    
    if ! $RUN_SLOW; then
        markers="$markers and not slow"
    fi
    
    if pytest -m "$markers" $extra_args; then
        echo -e "${GREEN}✓ $name passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $name failed${NC}"
        return 1
    fi
}

# Run test suites
TEST_FAILURES=0

# Unit Tests
if $RUN_UNIT; then
    echo ""
    echo -e "${YELLOW}=== Unit Tests ===${NC}"
    if run_pytest "Unit Tests" "unit or not (integration or e2e or security or race)" "tests/test_models.py"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
        ((TEST_FAILURES++))
    fi
fi

# Integration Tests
if $RUN_INTEGRATION; then
    echo ""
    echo -e "${YELLOW}=== Integration Tests ===${NC}"
    if run_pytest "Integration Tests" "integration or not (unit or e2e or security)" "tests/test_auth.py tests/test_bags.py tests/test_bills.py"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
        ((TEST_FAILURES++))
    fi
fi

# Security Tests
if $RUN_SECURITY; then
    echo ""
    echo -e "${YELLOW}=== Security Tests ===${NC}"
    if run_pytest "Security Tests" "security" "tests/test_security.py"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
        ((TEST_FAILURES++))
    fi
fi

# Race Condition Tests
if $RUN_INTEGRATION; then
    echo ""
    echo -e "${YELLOW}=== Race Condition Tests ===${NC}"
    if run_pytest "Race Condition Tests" "race" "tests/test_race_conditions.py"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
        ((TEST_FAILURES++))
    fi
fi

# Unicode Tests
if $RUN_INTEGRATION; then
    echo ""
    echo -e "${YELLOW}=== Unicode & Special Characters ===${NC}"
    if run_pytest "Unicode Tests" "unicode" "tests/test_unicode.py"; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
        ((TEST_FAILURES++))
    fi
fi

# Error Recovery Tests
if $RUN_INTEGRATION; then
    echo ""
    echo -e "${YELLOW}=== Error Recovery Tests ===${NC}"
    if pytest tests/test_error_recovery.py -v; then
        echo -e "${GREEN}✓ Error Recovery Tests passed${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}✗ Error Recovery Tests failed${NC}"
        ((FAILED_TESTS++))
        ((TEST_FAILURES++))
    fi
fi

# E2E Tests (Playwright)
if $RUN_E2E; then
    echo ""
    echo -e "${YELLOW}=== End-to-End Tests (Playwright) ===${NC}"
    
    # Check if Playwright tests exist
    if [ -f "test_critical_flows.py" ] || [ -f "test_mobile_viewport.py" ]; then
        echo "Running Playwright tests..."
        
        # Start server in background if needed
        if ! curl -s http://localhost:5000 > /dev/null 2>&1; then
            echo "Starting Flask server for E2E tests..."
            python main.py > /tmp/test_server.log 2>&1 &
            SERVER_PID=$!
            sleep 3
        fi
        
        # Run Playwright tests
        if python test_critical_flows.py && python test_mobile_viewport.py; then
            echo -e "${GREEN}✓ E2E Tests passed${NC}"
            ((PASSED_TESTS++))
        else
            echo -e "${RED}✗ E2E Tests failed${NC}"
            ((FAILED_TESTS++))
            ((TEST_FAILURES++))
        fi
        
        # Stop server if we started it
        if [ ! -z "$SERVER_PID" ]; then
            kill $SERVER_PID 2>/dev/null || true
        fi
    else
        echo "No Playwright tests found - skipping E2E tests"
    fi
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Test Results Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Test Categories:"
echo "  Passed: $PASSED_TESTS"
echo "  Failed: $FAILED_TESTS"
echo ""

if $GENERATE_COVERAGE; then
    echo -e "${YELLOW}Coverage report generated in htmlcov/index.html${NC}"
    echo ""
fi

if [ $TEST_FAILURES -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}✓ Ready for publishing${NC}"
    exit 0
else
    echo -e "${RED}✗ $TEST_FAILURES test category(ies) failed${NC}"
    echo -e "${RED}✗ Fix failures before publishing${NC}"
    exit 1
fi
