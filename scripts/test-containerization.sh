#!/bin/bash

# TraceTrack Containerization Test Script
# Comprehensive test of the containerization setup

set -e

echo "🧪 Testing TraceTrack Containerization..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_passed=0
test_failed=0

run_test() {
    local test_name=$1
    local test_command=$2
    
    echo -n "Testing $test_name... "
    
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((test_passed++))
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        ((test_failed++))
        return 1
    fi
}

# Test 1: Docker environment
echo "🔧 Testing Docker Environment..."
run_test "Docker availability" "docker --version"
run_test "Docker Compose availability" "docker compose version || docker-compose --version"

# Test 2: Build images
echo ""
echo "🏗️ Testing Image Builds..."
run_test "Production image build" "docker build -t tracetrack:test-prod -f Dockerfile ."
run_test "Development image build" "docker build -t tracetrack:test-dev -f Dockerfile.dev ."

# Test 3: SSL setup
echo ""
echo "🔐 Testing SSL Setup..."
run_test "SSL certificate generation" "./scripts/setup-ssl.sh && test -f docker/nginx/ssl/cert.pem"

# Test 4: Static assets
echo ""
echo "📁 Testing Static Asset Management..."
# Create a test container to verify entrypoint
docker create --name test-static -v test_static:/shared/static tracetrack:test-prod >/dev/null 2>&1
run_test "Static asset entrypoint" "docker start test-static && sleep 5 && docker exec test-static ls /shared/static"
docker rm -f test-static >/dev/null 2>&1
docker volume rm test_static >/dev/null 2>&1

# Test 5: Health endpoint
echo ""
echo "🏥 Testing Health Endpoints..."
# Start a minimal stack for testing
docker run -d --name test-health -p 15000:5000 tracetrack:test-prod >/dev/null 2>&1
sleep 10
run_test "Health endpoint response" "curl -f http://localhost:15000/health"
docker rm -f test-health >/dev/null 2>&1

# Test 6: Configuration validation
echo ""
echo "⚙️ Testing Configuration Files..."
run_test "Base compose syntax" "docker compose -f docker-compose.yml config"
run_test "Dev compose syntax" "docker compose -f docker-compose.yml -f docker-compose.dev.yml config"
run_test "Prod compose syntax" "docker compose -f docker-compose.yml -f docker-compose.prod.yml config"
run_test "Local compose syntax" "docker compose -f docker-compose.yml -f docker-compose.local.yml config"

# Test 7: Environment variables
echo ""
echo "🌍 Testing Environment Configuration..."
run_test ".env.example validity" "test -f .env.example && grep -q DATABASE_URL .env.example"

# Cleanup test images
echo ""
echo "🧹 Cleaning up test artifacts..."
docker rmi tracetrack:test-prod tracetrack:test-dev >/dev/null 2>&1 || true

# Summary
echo ""
echo "📊 Test Summary:"
echo -e "  ${GREEN}Passed: $test_passed${NC}"
if [ $test_failed -gt 0 ]; then
    echo -e "  ${RED}Failed: $test_failed${NC}"
    echo ""
    echo -e "${RED}❌ Containerization tests failed!${NC}"
    exit 1
else
    echo -e "  ${YELLOW}Failed: $test_failed${NC}"
    echo ""
    echo -e "${GREEN}✅ All containerization tests passed!${NC}"
    echo "🚀 The application is ready for containerized deployment."
fi