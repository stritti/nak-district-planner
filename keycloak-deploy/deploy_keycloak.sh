#!/bin/bash
# Keycloak Deployment & Setup Script
# Automatisiert Schritte 1.4–1.8 für VPS-Deployment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Parse arguments
KEYCLOAK_DIR="${1:-.}"
KEYCLOAK_URL="${2:-https://auth.5tritti.de}"
ADMIN_PASSWORD="${3:-}"

if [ -z "$ADMIN_PASSWORD" ]; then
    print_error "Missing required argument: ADMIN_PASSWORD"
    echo "Usage: ./deploy_keycloak.sh [KEYCLOAK_DIR] [KEYCLOAK_URL] [ADMIN_PASSWORD]"
    echo ""
    echo "Example:"
    echo "  ./deploy_keycloak.sh /opt/keycloak-deploy https://auth.5tritti.de mySecurePassword123"
    exit 1
fi

print_header "Keycloak VPS Deployment"

# Step 1: Check Docker
print_header "Step 1: Checking Docker"
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker."
    exit 1
fi
print_success "Docker is installed"

if ! command -v docker &> /dev/null; then
    print_error "docker command not found. Please install Docker."
    exit 1
fi
print_success "Docker is available (includes compose plugin)"

# Step 2: Setup directory
print_header "Step 2: Setting up keycloak-deploy directory"

if [ ! -d "$KEYCLOAK_DIR" ]; then
    mkdir -p "$KEYCLOAK_DIR"
    print_success "Created directory: $KEYCLOAK_DIR"
fi

cd "$KEYCLOAK_DIR"
print_success "Working in: $(pwd)"

# Step 3: Copy files from repo (if running from repo root)
print_header "Step 3: Checking configuration files"

if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found in $KEYCLOAK_DIR"
    print_warning "Copy files from keycloak-deploy/ first"
    exit 1
fi
print_success "docker-compose.yml found"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Created .env from .env.example"
    else
        print_error ".env and .env.example not found"
        exit 1
    fi
fi

# Step 4: Update .env with passwords
print_header "Step 4: Updating environment variables"

# Generate random DB password
DB_PASSWORD=$(echo $RANDOM | md5sum | cut -c1-16)

# Use sed to update passwords in .env
# Note: Using | as delimiter for URLs with /
sed -i.bak "s|KEYCLOAK_ADMIN_PASSWORD=.*|KEYCLOAK_ADMIN_PASSWORD=$ADMIN_PASSWORD|" .env
sed -i.bak "s|KEYCLOAK_DB_PASSWORD=.*|KEYCLOAK_DB_PASSWORD=$DB_PASSWORD|" .env
sed -i.bak "s|KC_HOSTNAME_URL=.*|KC_HOSTNAME_URL=$KEYCLOAK_URL|" .env

print_success ".env updated with credentials"

# Step 5: Start Docker Compose
# Note: Keycloak 26 automatically builds on first start with 'start' command
print_header "Step 5: Starting Keycloak & PostgreSQL containers"

docker compose up -d
print_success "Containers started"

# Step 6: Wait for Keycloak to be ready
# First start may take longer due to automatic build phase
print_header "Step 6: Waiting for Keycloak to start (this may take 60-120 seconds on first start)"

# First, wait for HTTP endpoint to respond
max_retries=120
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -s "$KEYCLOAK_URL/" > /dev/null 2>&1; then
        print_success "Keycloak HTTP endpoint is responding"
        break
    fi
    
    retry_count=$((retry_count + 1))
    echo -ne "  Waiting for HTTP endpoint... Attempt $retry_count/$max_retries\r"
    sleep 1
done

if [ $retry_count -eq $max_retries ]; then
    print_error "Keycloak HTTP endpoint did not respond within timeout"
    echo "Check logs with: docker compose logs -f keycloak"
    exit 1
fi

# Second, wait for authentication endpoint to be ready (indicates full initialization)
print_header "Step 6b: Waiting for Keycloak authentication to be ready"

retry_count=0
max_retries=60

while [ $retry_count -lt $max_retries ]; do
    # Try to get a token - this will only work when Keycloak is fully ready
    response=$(curl -s -w "\n%{http_code}" -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d 'client_id=admin-cli&grant_type=password&username=admin&password=dummy' 2>&1)
    
    http_code=$(echo "$response" | tail -n1)
    
    # Keycloak is ready if we get 400 (bad credentials) instead of 404 or 502
    if [ "$http_code" = "400" ] || [ "$http_code" = "200" ]; then
        print_success "Keycloak authentication endpoint is ready!"
        break
    fi
    
    retry_count=$((retry_count + 1))
    echo -ne "  Waiting for auth endpoint... Attempt $retry_count/$max_retries (HTTP $http_code)\r"
    sleep 1
done

if [ $retry_count -eq $max_retries ]; then
    print_error "Keycloak authentication endpoint did not become ready"
    echo "Check logs with: docker compose logs -f keycloak"
    echo "Last HTTP code: $http_code"
    exit 1
fi

# Step 7: Check Traefik network
print_header "Step 8: Checking Traefik network"

if docker network inspect traefik_net > /dev/null 2>&1; then
    print_success "Traefik network found"
else
    print_error "Traefik network 'traefik_net' not found"
    print_warning "Make sure Traefik is running and network is named 'traefik_net'"
    exit 1
fi

# Step 8: Run Realm Setup Script
print_header "Step 9: Setting up Keycloak Realm"

if [ -f "setup_keycloak_realm.py" ]; then
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3."
        exit 1
    fi
    
    # Install requests if not available
    if ! python3 -c "import requests" 2>/dev/null; then
        print_warning "Installing requests library..."
        pip3 install requests > /dev/null 2>&1 || pip install requests > /dev/null 2>&1
    fi
    
    print_success "Running realm setup..."
    python3 setup_keycloak_realm.py \
        --keycloak-url "$KEYCLOAK_URL" \
        --admin-password "$ADMIN_PASSWORD"
else
    print_warning "setup_keycloak_realm.py not found, skipping auto-setup"
    print_warning "Manual setup: https://auth.5tritti.de/admin/"
fi

print_header "Deployment Complete!"

echo -e "${GREEN}Keycloak is now running at: ${BLUE}$KEYCLOAK_URL${NC}"
echo -e "${GREEN}Admin Console: ${BLUE}$KEYCLOAK_URL/admin/${NC}\n"

echo "Next steps:"
echo "1. Copy the CLIENT_SECRET from above"
echo "2. Add to nak-district-planner/.env:"
echo "   KEYCLOAK_URL=$KEYCLOAK_URL"
echo "   KEYCLOAK_REALM=nak-planner"
echo "   KEYCLOAK_CLIENT_ID=nak-planner-api"
echo "   KEYCLOAK_CLIENT_SECRET=<copied-secret>"
echo ""
echo "3. Verify JWKS endpoint:"
echo "   curl $KEYCLOAK_URL/realms/nak-planner/.well-known/jwks.json"
echo ""
echo "Troubleshooting:"
echo "  - Logs: docker compose logs -f keycloak"
echo "  - Health: curl $KEYCLOAK_URL/health"
echo ""
