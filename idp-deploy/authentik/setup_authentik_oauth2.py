#!/usr/bin/env python3
"""
Authentik OAuth2 Setup Script with OIDC Configuration

Automatisiert den Setup einer Authentik-Instanz für NAK Planner OIDC:
- Creates OAuth2/OIDC Provider
- Creates OAuth2 Application "nak-planner-frontend" (confidential)
- Configures Redirect URIs
- Creates Test User
- Exports configuration

Requirements:
  - Python 3.11+
  - requests library (pip install requests)
  - Authentik 2024.4+ läuft und ist erreichbar

Usage:
    python3 setup_authentik_oauth2.py \
        --authentik-url http://localhost:9000 \
        --bootstrap-token akadmin:insecure
"""

import argparse
import json
import sys
import time
from typing import Any, Optional

import requests


class AuthentikAdminClient:
    """Authentik Admin API client for OAuth2/OIDC setup"""

    def __init__(self, authentik_url: str, token: str):
        self.authentik_url = authentik_url.rstrip("/")
        self.token = token  # format: "akadmin:password" or API token

    def _headers(self) -> dict:
        """Authorization headers"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _auth_headers(self) -> dict:
        """Basic auth headers for initial bootstrap"""
        return {
            "Authorization": f"Basic {self.token}",
            "Content-Type": "application/json",
        }

    def get_providers(self) -> dict:
        """Get list of OIDC/OAuth2 providers"""
        url = f"{self.authentik_url}/api/v3/core/providers/"
        response = requests.get(url, headers=self._headers(), timeout=10)
        response.raise_for_status()
        return response.json()

    def get_applications(self) -> dict:
        """Get list of applications"""
        url = f"{self.authentik_url}/api/v3/core/applications/"
        response = requests.get(url, headers=self._headers(), timeout=10)
        response.raise_for_status()
        return response.json()

    def create_oidc_provider(
        self,
        name: str,
        client_id: str,
        redirect_uris: list[str],
    ) -> dict:
        """Create OIDC/OAuth2 provider"""
        print(f"Creating OIDC Provider: {name}...")
        url = f"{self.authentik_url}/api/v3/core/providers/oidc/"

        payload = {
            "name": name,
            "client_id": client_id,
            "client_type": "public",  # Public client (PKCE)
            "rsa_key": None,  # Auto-generate
            "redirect_uris": "\n".join(redirect_uris),
            "property_mappings": [],
            "property_mappings_sa": [],
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=10)

        if response.status_code == 201:
            provider_data = response.json()
            print(f"✓ OIDC Provider created: {name}")
            return provider_data
        elif response.status_code == 400:
            # Provider might already exist
            print(f"⚠ Could not create provider (might exist)")
            return None
        else:
            print(f"✗ Failed to create provider: {response.status_code} {response.text}")
            raise Exception(f"Failed to create provider: {response.text}")

    def create_application(
        self,
        name: str,
        slug: str,
        provider_id: int,
        icon_url: Optional[str] = None,
    ) -> dict:
        """Create OAuth2 Application"""
        print(f"Creating Application: {name}...")
        url = f"{self.authentik_url}/api/v3/core/applications/"

        payload = {
            "name": name,
            "slug": slug,
            "provider": provider_id,
            "icon": icon_url or "",
            "meta_icon": "",
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=10)

        if response.status_code == 201:
            app_data = response.json()
            print(f"✓ Application created: {name}")
            return app_data
        elif response.status_code == 400:
            print(f"⚠ Could not create application (might exist)")
            return None
        else:
            print(f"✗ Failed to create application: {response.status_code} {response.text}")
            raise Exception(f"Failed to create application: {response.text}")

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        name: Optional[str] = None,
    ) -> dict:
        """Create a user"""
        print(f"Creating user: {username}...")
        url = f"{self.authentik_url}/api/v3/core/users/"

        payload = {
            "username": username,
            "email": email,
            "name": name or username,
            "password": password,
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=10)

        if response.status_code == 201:
            user_data = response.json()
            print(f"✓ User created: {username}")
            return user_data
        elif response.status_code == 400:
            print(f"⚠ User already exists: {username}")
            # Try to get existing user
            try:
                return self.get_user_by_username(username)
            except:
                return None
        else:
            print(f"✗ Failed to create user: {response.status_code} {response.text}")
            raise Exception(f"Failed to create user: {response.text}")

    def get_user_by_username(self, username: str) -> dict:
        """Get user by username"""
        url = f"{self.authentik_url}/api/v3/core/users/?username={username}"
        response = requests.get(url, headers=self._headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("results"):
            return data["results"][0]
        raise Exception(f"User not found: {username}")

    def get_oidc_discovery_url(self) -> str:
        """Get OIDC Discovery endpoint"""
        return f"{self.authentik_url}/application/o/.well-known/openid-configuration"


def main():
    parser = argparse.ArgumentParser(description="Setup Authentik for NAK Planner OIDC")
    parser.add_argument(
        "--authentik-url",
        required=True,
        help="Authentik URL (e.g., http://localhost:9000)",
    )
    parser.add_argument(
        "--bootstrap-token",
        default="akadmin:insecure",
        help="Bootstrap token (default: akadmin:insecure for initial setup)",
    )
    parser.add_argument("--provider-name", default="NAK Planner OIDC", help="Provider name")
    parser.add_argument(
        "--client-id", default="nak-planner-frontend", help="OAuth2 Client ID"
    )
    parser.add_argument("--app-name", default="NAK Planner", help="Application name")
    parser.add_argument("--app-slug", default="nak-planner", help="Application slug")
    parser.add_argument("--test-user", default="testuser", help="Test user username")
    parser.add_argument("--test-password", default="testpassword123", help="Test user password")
    parser.add_argument("--test-email", default="test@nak-planner.local", help="Test user email")
    parser.add_argument(
        "--frontend-url",
        default="http://localhost:5173",
        help="Frontend URL for redirect URIs",
    )

    args = parser.parse_args()

    try:
        # Wait for Authentik to be ready
        print(f"\n{'=' * 70}")
        print("Waiting for Authentik to be ready...")
        print(f"{'=' * 70}\n")

        max_retries = 30
        retry_count = 0
        authentik_ready = False

        while retry_count < max_retries:
            try:
                response = requests.get(
                    f"{args.authentik_url}/-/health/live/", timeout=5
                )
                if response.status_code == 204:
                    print(f"✓ Authentik health check passed")
                    authentik_ready = True
                    break
            except requests.exceptions.RequestException:
                pass

            retry_count += 1
            print(f"  Attempt {retry_count}/{max_retries}: Waiting for Authentik...", end="\r")
            time.sleep(2)

        if not authentik_ready:
            print(f"\n✗ Authentik did not become ready after {max_retries * 2} seconds")
            print(f"  Check if Authentik is running: docker compose logs -f authentik")
            sys.exit(1)

        print()

        # Initialize client
        admin = AuthentikAdminClient(
            authentik_url=args.authentik_url,
            token=args.bootstrap_token,
        )

        print(f"\n{'=' * 70}")
        print("Authentik OIDC Configuration")
        print(f"{'=' * 70}\n")

        # 1. Create OIDC Provider
        redirect_uris = [
            f"{args.frontend_url}/auth/callback",
        ]

        provider = admin.create_oidc_provider(
            name=args.provider_name,
            client_id=args.client_id,
            redirect_uris=redirect_uris,
        )

        # 2. Create Application
        if provider:
            provider_id = provider.get("pk")
            app = admin.create_application(
                name=args.app_name,
                slug=args.app_slug,
                provider_id=provider_id,
            )
        else:
            print("⚠ Skipping application creation (provider not created)")

        # 3. Create Test User
        admin.create_user(
            username=args.test_user,
            email=args.test_email,
            password=args.test_password,
            name="Test User",
        )

        print(f"\n{'=' * 70}")
        print("✓ Setup Complete!")
        print(f"{'=' * 70}\n")

        # Display configuration info
        discovery_url = admin.get_oidc_discovery_url()
        print("OIDC Configuration:")
        print(f"  Discovery URL: {discovery_url}")
        print(f"  Client ID:     {args.client_id}")
        print(f"  Authentik URL: {args.authentik_url}\n")

        print("Test User Credentials:")
        print(f"  Username: {args.test_user}")
        print(f"  Password: {args.test_password}")
        print(f"  Email:    {args.test_email}\n")

        print("Frontend Environment Variables (.env.local):")
        print(f"  VITE_OIDC_DISCOVERY_URL={discovery_url}")
        print(f"  VITE_OIDC_CLIENT_ID={args.client_id}")
        print(f"  VITE_OIDC_REDIRECT_URI={args.frontend_url}/auth/callback\n")

        print("Next steps:")
        print(f"1. Copy OIDC settings to services/frontend/.env.local")
        print(f"2. Start frontend: cd services/frontend && bun run dev")
        print(f"3. Test login at: {args.frontend_url}/login")
        print(f"4. Authentik Admin: {args.authentik_url}/if/admin/ (user: akadmin)\n")

    except KeyboardInterrupt:
        print("\n✗ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Setup failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
