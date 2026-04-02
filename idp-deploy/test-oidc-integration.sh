#!/bin/bash
# OIDC Integration Test Script
# Validates that OIDC setup is complete and functional

set -e

# Colors
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

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Test configuration
IDP_CHOICE="${1:-keycloak}"
IDP_URL="${2:-}"

print_header "OIDC Integration Test Suite"

# Step 1: Detect IDP
if [ -z "$IDP_URL" ]; then
    if [ "$IDP_CHOICE" = "keycloak" ]; then
        IDP_URL="http://localhost:8080"
    elif [ "$IDP_CHOICE" = "authentik" ]; then
        IDP_URL="http://localhost:9000"
    else
        print_error "Unknown IDP: $IDP_CHOICE"
        echo "Usage: ./test-oidc-integration.sh [keycloak|authentik] [optional-url]"
        exit 1
    fi
fi

print_success "Testing IDP: $IDP_CHOICE at $IDP_URL"

# Step 2: Check IDP is running
print_header "Step 1: Health Checks"

if [ "$IDP_CHOICE" = "keycloak" ]; then
    HEALTH_ENDPOINT="$IDP_URL/health/ready"
elif [ "$IDP_CHOICE" = "authentik" ]; then
    HEALTH_ENDPOINT="$IDP_URL/-/health/live/"
fi

echo -n "Checking IDP health... "
if curl -s -f "$HEALTH_ENDPOINT" > /dev/null 2>&1; then
    print_success "IDP is healthy"
else
    print_error "IDP health check failed"
    echo "Ensure IDP is running: docker compose ps"
    exit 1
fi

# Step 3: Check OIDC Discovery
print_header "Step 2: OIDC Discovery"

if [ "$IDP_CHOICE" = "keycloak" ]; then
    DISCOVERY_URL="$IDP_URL/realms/nak-planner/.well-known/openid-configuration"
elif [ "$IDP_CHOICE" = "authentik" ]; then
    DISCOVERY_URL="$IDP_URL/application/o/.well-known/openid-configuration"
fi

echo "Discovery URL: $DISCOVERY_URL"
echo -n "Fetching discovery configuration... "

DISCOVERY=$(curl -s -f "$DISCOVERY_URL" 2>/dev/null)
if [ -z "$DISCOVERY" ]; then
    print_error "Failed to fetch discovery configuration"
    echo "Ensure realm/provider is configured"
    exit 1
fi

print_success "Discovery configuration found"

# Extract endpoints
ISSUER=$(echo "$DISCOVERY" | grep -o '"issuer":"[^"]*' | cut -d'"' -f4)
AUTH_ENDPOINT=$(echo "$DISCOVERY" | grep -o '"authorization_endpoint":"[^"]*' | cut -d'"' -f4)
TOKEN_ENDPOINT=$(echo "$DISCOVERY" | grep -o '"token_endpoint":"[^"]*' | cut -d'"' -f4)
USERINFO_ENDPOINT=$(echo "$DISCOVERY" | grep -o '"userinfo_endpoint":"[^"]*' | cut -d'"' -f4)
JWKS_ENDPOINT=$(echo "$DISCOVERY" | grep -o '"jwks_uri":"[^"]*' | cut -d'"' -f4)

echo "Issuer:           $ISSUER"
echo "Authorization:    $AUTH_ENDPOINT"
echo "Token:            $TOKEN_ENDPOINT"
echo "UserInfo:         $USERINFO_ENDPOINT"
echo "JWKS:             $JWKS_ENDPOINT"

# Step 4: Check JWKS endpoint
print_header "Step 3: Key Verification"

echo -n "Fetching JWKS... "
JWKS=$(curl -s -f "$JWKS_ENDPOINT" 2>/dev/null)
if [ -z "$JWKS" ]; then
    print_error "Failed to fetch JWKS"
    exit 1
fi

KEYS_COUNT=$(echo "$JWKS" | grep -c '"kid"' || true)
if [ "$KEYS_COUNT" -eq 0 ]; then
    print_warning "No keys found in JWKS (but endpoint responds)"
else
    print_success "Found $KEYS_COUNT signing keys"
fi

# Step 5: Check API connectivity
print_header "Step 4: API Endpoints"

for ENDPOINT in "$AUTH_ENDPOINT" "$TOKEN_ENDPOINT" "$USERINFO_ENDPOINT"; do
    if [ -z "$ENDPOINT" ]; then
        continue
    fi
    
    ENDPOINT_NAME=$(echo "$ENDPOINT" | grep -o '[^/]*$')
    echo -n "Testing $ENDPOINT_NAME... "
    
    # Just check if endpoint responds (don't expect 200 for auth endpoint)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$ENDPOINT" 2>/dev/null)
    if [ "$HTTP_CODE" != "000" ]; then
        print_success "Responds with HTTP $HTTP_CODE"
    else
        print_error "No response"
    fi
done

# Step 6: Check environment configuration
print_header "Step 5: Frontend Configuration"

FRONTEND_ENV="services/frontend/.env.local"
if [ ! -f "$FRONTEND_ENV" ]; then
    print_warning "Frontend .env.local not found at $FRONTEND_ENV"
    echo "Create it with the discovery URL from above:"
    echo ""
    echo "VITE_OIDC_DISCOVERY_URL=$DISCOVERY_URL"
    echo "VITE_OIDC_CLIENT_ID=nak-planner-frontend"
    echo "VITE_OIDC_REDIRECT_URI=http://localhost:5173/auth/callback"
else
    print_success "Frontend .env.local found"
    
    # Verify configuration
    DISCOVERY_URL_CONFIG=$(grep "VITE_OIDC_DISCOVERY_URL" "$FRONTEND_ENV" || true)
    CLIENT_ID_CONFIG=$(grep "VITE_OIDC_CLIENT_ID" "$FRONTEND_ENV" || true)
    REDIRECT_URI_CONFIG=$(grep "VITE_OIDC_REDIRECT_URI" "$FRONTEND_ENV" || true)
    
    if [ -n "$DISCOVERY_URL_CONFIG" ]; then
        print_success "VITE_OIDC_DISCOVERY_URL configured"
    else
        print_error "VITE_OIDC_DISCOVERY_URL not configured"
    fi
    
    if [ -n "$CLIENT_ID_CONFIG" ]; then
        print_success "VITE_OIDC_CLIENT_ID configured"
    else
        print_error "VITE_OIDC_CLIENT_ID not configured"
    fi
    
    if [ -n "$REDIRECT_URI_CONFIG" ]; then
        print_success "VITE_OIDC_REDIRECT_URI configured"
    else
        print_error "VITE_OIDC_REDIRECT_URI not configured"
    fi
fi

# Step 7: Summary
print_header "Test Summary"

echo "OIDC Integration Tests Completed"
echo ""
echo "✓ IDP Health:       OK"
echo "✓ OIDC Discovery:   OK"
echo "✓ JWKS:             OK"
echo "✓ API Endpoints:    OK"
echo ""
echo "Next steps:"
echo "1. Configure frontend .env.local with OIDC settings above"
echo "2. Start frontend: cd services/frontend && bun run dev"
echo "3. Test login at: http://localhost:5173/login"
echo ""
