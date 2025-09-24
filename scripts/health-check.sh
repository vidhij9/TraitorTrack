#!/bin/bash

# TraceTrack Health Check Script
# Validates all services are running correctly

set -e

echo "🏥 TraceTrack Health Check..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local service=$1
    local url=$2
    local expected=$3
    
    echo -n "Checking $service... "
    
    if curl -sf "$url" | grep -q "$expected"; then
        echo -e "${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e "${RED}❌ FAILED${NC}"
        return 1
    fi
}

check_docker_service() {
    local service=$1
    
    echo -n "Checking Docker service $service... "
    
    # Try modern docker compose first, fallback to legacy docker-compose
    if command -v docker >/dev/null 2>&1; then
        if docker compose ps 2>/dev/null | grep -q "$service.*running" || docker-compose ps 2>/dev/null | grep -q "$service.*Up"; then
            echo -e "${GREEN}✅ OK${NC}"
            return 0
        else
            echo -e "${RED}❌ FAILED${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️ Docker not available${NC}"
        return 1
    fi
}

# Check Docker services
echo "🐳 Docker Services:"
check_docker_service "web"
check_docker_service "db"
check_docker_service "redis"
check_docker_service "nginx"

echo ""

# Check application endpoints
echo "🌐 Application Endpoints:"
check_service "Health Check" "http://localhost:5000/health" "TraceTrack"
check_service "Login Page" "http://localhost:5000/login" "TraceTrack"
check_service "API Stats" "http://localhost:5000/api/stats" "total_bags"

echo ""

# Check database connectivity
echo "💾 Database Connectivity:"
if (docker compose exec -T db pg_isready -U tracetrack_user -d tracetrack_db 2>/dev/null || docker-compose exec -T db pg_isready -U tracetrack_user -d tracetrack_db 2>/dev/null) > /dev/null 2>&1; then
    echo -e "Database Connection: ${GREEN}✅ OK${NC}"
else
    echo -e "Database Connection: ${RED}❌ FAILED${NC}"
fi

# Check Redis connectivity
echo "🔴 Redis Connectivity:"
if (docker compose exec -T redis redis-cli ping 2>/dev/null || docker-compose exec -T redis redis-cli ping 2>/dev/null) | grep -q "PONG"; then
    echo -e "Redis Connection: ${GREEN}✅ OK${NC}"
else
    echo -e "Redis Connection: ${RED}❌ FAILED${NC}"
fi

echo ""
echo "📊 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

echo ""
echo "🏁 Health check completed!"