#!/bin/bash
# Authentik Deployment & Setup Script
# Automatisiert VPS-Deployment mit OIDC-Konfiguration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
AUTHENTIK_DIR="${1:-.}"
AUTHENTIK_URL="${2:-http://localhost:9000}"
SECRET_KEY="${3:-}"

if [ -z "$SECRET_KEY" ]; then
    print_error "Missing required argument: SECRET_KEY"
    echo "Usage: ./deploy_authentik.sh [AUTHENTIK_DIR] [AUTHENTIK_URL] [SECRET_KEY]"
    echo ""
    echo "Generate SECRET_KEY with: openssl rand -base64 32"
    echo ""
    echo "Example:"
    echo "  ./deploy_authentik.sh /opt/authentik http://localhost:9000 \$(openssl rand -base64 32)"
    exit 1
fi

print_header "Authentik VPS Deployment"

# Step 1: Check Docker
print_header "Step 1: Checking Docker"
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install Docker."
    exit 1
fi
print_success "Docker is installed"

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "docker compose not found"
    exit 1
fi
print_success "Docker Compose is available"

# Step 2: Setup directory
print_header "Step 2: Setting up authentik directory"

if [ ! -d "$AUTHENTIK_DIR" ]; then
    mkdir -p "$AUTHENTIK_DIR"
    print_success "Created directory: $AUTHENTIK_DIR"
fi

cd "$AUTHENTIK_DIR"
print_success "Working in: $(pwd)"

# Step 3: Check configuration files
print_header "Step 3: Checking configuration files"

if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found in $AUTHENTIK_DIR"
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

# Step 4: Update .env with secrets
print_header "Step 4: Updating environment variables"

sed -i.bak "s|AUTHENTIK_SECRET_KEY=.*|AUTHENTIK_SECRET_KEY=$SECRET_KEY|" .env

print_success ".env updated with secret key"

# Step 5: Start Docker Compose
print_header "Step 5: Starting Authentik services"

docker compose up -d
print_success "Containers started"

# Step 6: Wait for Authentik to be ready
print_header "Step 6: Waiting for Authentik to start (this may take 30-60 seconds)"

max_retries=60
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -s "$AUTHENTIK_URL/-/health/live/" -o /dev/null -w "%{http_code}" | grep -q "204"; then
        print_success "Authentik health check passed"
        break
    fi
    
    retry_count=$((retry_count + 1))
    echo -ne "  Waiting for Authentik... Attempt $retry_count/$max_retries\r"
    sleep 1
done

if [ $retry_count -eq $max_retries ]; then
    print_error "Authentik did not become ready within timeout"
    echo "Check logs with: docker compose logs -f authentik"
    exit 1
fi

print()  # newline after progress indicator

# Step 7: Run Setup Script
print_header "Step 8: Setting up OAuth2 Provider"

if [ -f "setup_authentik_oauth2.py" ]; then
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3."
        exit 1
    fi
    
    if ! python3 -c "import requests" 2>/dev/null; then
        print_warning "Installing requests library..."
        pip3 install requests > /dev/null 2>&1 || pip install requests > /dev/null 2>&1
    fi
    
    print_success "Running OAuth2 setup..."
    python3 setup_authentik_oauth2.py \
        --authentik-url "$AUTHENTIK_URL" \
        --bootstrap-token "akadmin:insecure"
else
    print_warning "setup_authentik_oauth2.py not found, skipping auto-setup"
    print_warning "Manual setup: $AUTHENTIK_URL/if/admin/"
fi

print_header "Deployment Complete!"

echo -e "${GREEN}Authentik is now running at: ${BLUE}$AUTHENTIK_URL${NC}"
echo -e "${GREEN}Admin Console: ${BLUE}$AUTHENTIK_URL/if/admin/${NC}\n"

echo "Next steps:"
echo "1. Change bootstrap password in Admin Console:"
echo "   $AUTHENTIK_URL/if/admin/ (user: akadmin, password: insecure)"
echo ""
echo "2. Copy the OIDC settings from above to services/frontend/.env.local"
echo ""
echo "3. Start frontend:"
echo "   cd services/frontend && bun run dev"
echo ""
echo "4. Test login at: http://localhost:5173/login"
echo ""
echo "Troubleshooting:"
echo "  - Logs: docker compose logs -f authentik"
echo "  - Health: curl $AUTHENTIK_URL/-/health/live/"
echo ""
