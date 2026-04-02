#!/usr/bin/env python3
"""
Keycloak Realm Setup Script with OIDC Configuration

Automatisiert den Setup eines Keycloak-Realms für NAK Planner OIDC:
- Erstellt Realm "nak-planner"
- Erstellt OIDC Client "nak-planner-frontend" (Public für PKCE)
- Konfiguriert Redirect URIs für Auth Callback
- Konfiguriert Logout URIs
- Erstellt Test-User
- Exportiert Realm-Config

Requirements:
  - Python 3.11+
  - requests library (pip install requests)
  - Keycloak 26.5+ läuft und ist erreichbar

Usage:
    python3 setup_keycloak_realm.py --keycloak-url http://localhost:8080 \
        --admin-password admin_dev_pw
"""

import argparse
import json
import sys
import time
from typing import Any, Optional

import requests


class KeycloakAdminClient:
    """Keycloak Admin API client with OIDC support"""

    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        admin_user: str,
        admin_password: str,
        client_id: str = "admin-cli",
    ):
        self.keycloak_url = keycloak_url.rstrip("/")
        self.realm = realm
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.client_id = client_id
        self.token: Optional[str] = None
        self.token_expires_at = 0

    def _get_token(self) -> str:
        """Get admin access token via password grant"""
        if self.token and time.time() < self.token_expires_at:
            return self.token

        url = f"{self.keycloak_url}/realms/master/protocol/openid-connect/token"
        data = {
            "client_id": self.client_id,
            "grant_type": "password",
            "username": self.admin_user,
            "password": self.admin_password,
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
        except requests.exceptions.ConnectionError as e:
            print(f"\n✗ Cannot connect to Keycloak at {self.keycloak_url}")
            print(f"  Error: {e}")
            print(f"  Make sure Keycloak is running and the URL is correct.")
            raise
        except requests.exceptions.HTTPError as e:
            print(f"\n✗ Keycloak returned error: {response.status_code}")
            print(f"  URL: {url}")
            print(f"  Response: {response.text}")
            raise

        token_data = response.json()
        self.token = token_data["access_token"]
        self.token_expires_at = time.time() + token_data.get("expires_in", 3600) - 60
        return self.token

    def _headers(self) -> dict:
        """Authorization headers"""
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    def create_realm(self, realm_name: str, display_name: Optional[str] = None) -> dict:
        """Create a new realm with OIDC-friendly settings"""
        print(f"Creating realm: {realm_name}...")
        url = f"{self.keycloak_url}/admin/realms"
        payload = {
            "realm": realm_name,
            "displayName": display_name or realm_name,
            "enabled": True,
            "sslRequired": "external",
            # OIDC-friendly defaults
            "defaultRole": {
                "name": "default-roles-" + realm_name,
                "description": "Default roles for all users"
            },
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=10)

        if response.status_code == 201:
            print(f"✓ Realm created: {realm_name}")
            return {"realm": realm_name, "status": "created"}
        elif response.status_code == 409:
            print(f"⚠ Realm already exists: {realm_name}")
            return {"realm": realm_name, "status": "exists"}
        else:
            print(f"✗ Failed to create realm: {response.status_code} {response.text}")
            raise Exception(f"Failed to create realm: {response.text}")

    def get_realm(self, realm_name: str) -> dict:
        """Get realm details"""
        url = f"{self.keycloak_url}/admin/realms/{realm_name}"
        response = requests.get(url, headers=self._headers(), timeout=10)
        response.raise_for_status()
        return response.json()

    def create_oidc_public_client(
        self,
        realm_name: str,
        client_id: str,
        redirect_uris: list[str],
        logout_redirect_uris: Optional[list[str]] = None,
    ) -> dict:
        """Create a public OIDC client (for PKCE flow in frontend)"""
        print(f"Creating OIDC client: {client_id} in realm {realm_name}...")
        url = f"{self.keycloak_url}/admin/realms/{realm_name}/clients"

        payload = {
            "clientId": client_id,
            "name": client_id,
            "description": "NAK Planner Frontend (OIDC Public Client)",
            "enabled": True,
            "public": True,  # PUBLIC CLIENT (no client_secret)
            # Protocol settings
            "protocol": "openid-connect",
            "accessType": "PUBLIC",
            # Flow settings
            "standardFlowEnabled": True,
            "implicitFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "serviceAccountsEnabled": False,
            "authorizationServicesEnabled": False,
            # PKCE (required for public clients)
            "attributes": {
                "pkce.code.challenge.method": "S256",
            },
            # Redirect URIs
            "redirectUris": redirect_uris,
            "webOrigins": ["+"],  # Allow all origins
            "validRedirectUris": redirect_uris,
        }

        if logout_redirect_uris:
            payload["attributes"]["post.logout.redirect.uris"] = " ".join(logout_redirect_uris)

        response = requests.post(url, json=payload, headers=self._headers(), timeout=10)

        if response.status_code == 201:
            client_data = response.json()
            print(f"✓ OIDC Client created: {client_id}")
            return client_data
        elif response.status_code == 409:
            print(f"⚠ Client already exists: {client_id}")
            existing = self.get_client_by_id(realm_name, client_id)
            return existing
        else:
            print(f"✗ Failed to create client: {response.status_code} {response.text}")
            raise Exception(f"Failed to create client: {response.text}")

    def get_client_by_id(self, realm_name: str, client_id: str) -> dict:
        """Get client by clientId"""
        url = f"{self.keycloak_url}/admin/realms/{realm_name}/clients?clientId={client_id}"
        response = requests.get(url, headers=self._headers(), timeout=10)
        response.raise_for_status()
        clients = response.json()
        if clients:
            return clients[0]
        raise Exception(f"Client not found: {client_id}")

    def get_client_secret(self, realm_name: str, client_uuid: str) -> str:
        """Get client secret (N/A for public clients)"""
        url = (
            f"{self.keycloak_url}/admin/realms/{realm_name}/clients/{client_uuid}"
            f"/client-secret"
        )
        try:
            response = requests.get(url, headers=self._headers(), timeout=10)
            response.raise_for_status()
            data = response.json()
            return data["value"]
        except:
            return None  # Public clients don't have secrets

    def create_user(
        self,
        realm_name: str,
        username: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> dict:
        """Create a user and set password"""
        print(f"Creating user: {username}...")
        url = f"{self.keycloak_url}/admin/realms/{realm_name}/users"

        payload = {
            "username": username,
            "email": email,
            "emailVerified": True,
            "enabled": True,
            "firstName": first_name or username,
            "lastName": last_name or "",
        }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=10)

        if response.status_code == 201:
            user_data = response.json()
            user_id = response.headers.get("Location", "").split("/")[-1]
            print(f"✓ User created: {username}")

            # Set password
            self._set_user_password(realm_name, user_id, password)
            return {"username": username, "email": email, "user_id": user_id}

        elif response.status_code == 409:
            print(f"⚠ User already exists: {username}")
            user = self.get_user_by_username(realm_name, username)
            return user
        else:
            print(f"✗ Failed to create user: {response.status_code} {response.text}")
            raise Exception(f"Failed to create user: {response.text}")

    def _set_user_password(self, realm_name: str, user_id: str, password: str) -> None:
        """Set user password"""
        url = f"{self.keycloak_url}/admin/realms/{realm_name}/users/{user_id}/reset-password"
        payload = {"type": "password", "value": password, "temporary": False}

        response = requests.put(url, json=payload, headers=self._headers(), timeout=10)
        response.raise_for_status()
        print(f"  - Password set")

    def get_user_by_username(self, realm_name: str, username: str) -> dict:
        """Get user by username"""
        url = f"{self.keycloak_url}/admin/realms/{realm_name}/users?username={username}"
        response = requests.get(url, headers=self._headers(), timeout=10)
        response.raise_for_status()
        users = response.json()
        if users:
            return users[0]
        raise Exception(f"User not found: {username}")

    def export_realm(self, realm_name: str, output_file: str) -> None:
        """Export realm config"""
        print(f"Exporting realm to {output_file}...")
        url = (
            f"{self.keycloak_url}/admin/realms/{realm_name}/partial-export?"
            f"exportClients=true&exportGroupsAndRoles=true"
        )
        response = requests.get(url, headers=self._headers(), timeout=10)
        response.raise_for_status()

        with open(output_file, "w") as f:
            json.dump(response.json(), f, indent=2)

        print(f"✓ Realm exported to {output_file}")

    def get_oidc_discovery_url(self, realm_name: str) -> str:
        """Get OIDC Discovery endpoint"""
        return f"{self.keycloak_url}/realms/{realm_name}/.well-known/openid-configuration"


def main():
    parser = argparse.ArgumentParser(description="Setup Keycloak realm for NAK Planner OIDC")
    parser.add_argument(
        "--keycloak-url",
        required=True,
        help="Keycloak URL (e.g., http://localhost:8080 or https://auth.example.com)",
    )
    parser.add_argument("--admin-user", default="admin", help="Keycloak admin username")
    parser.add_argument(
        "--admin-password",
        required=True,
        help="Keycloak admin password",
    )
    parser.add_argument("--realm-name", default="nak-planner", help="Realm name")
    parser.add_argument("--client-id", default="nak-planner-frontend", help="OIDC Client ID")
    parser.add_argument("--test-user", default="testuser", help="Test user username")
    parser.add_argument(
        "--test-password", default="testpassword123", help="Test user password"
    )
    parser.add_argument(
        "--test-email", default="test@nak-planner.local", help="Test user email"
    )
    parser.add_argument(
        "--frontend-url",
        default="http://localhost:5173",
        help="Frontend URL for redirect URIs (dev: http://localhost:5173)",
    )
    parser.add_argument(
        "--output-file",
        default="realm-export.json",
        help="Output file for realm export",
    )

    args = parser.parse_args()

    try:
        # Wait for Keycloak to be ready before attempting setup
        print(f"\n{'=' * 70}")
        print("Waiting for Keycloak to be ready...")
        print(f"{'=' * 70}\n")

        max_retries = 30
        retry_count = 0
        keycloak_ready = False

        while retry_count < max_retries:
            try:
                response = requests.get(f"{args.keycloak_url}/health/ready", timeout=5)
                if response.status_code == 200:
                    print(f"✓ Keycloak health check passed")
                    keycloak_ready = True
                    break
            except requests.exceptions.RequestException:
                pass

            retry_count += 1
            print(f"  Attempt {retry_count}/{max_retries}: Waiting for Keycloak...", end="\r")
            time.sleep(2)

        if not keycloak_ready:
            print(f"\n✗ Keycloak did not become ready after {max_retries * 2} seconds")
            print(f"  Check if Keycloak is running: docker compose logs -f keycloak")
            sys.exit(1)

        print()  # newline after progress indicator

        # Initialize admin client
        admin = KeycloakAdminClient(
            keycloak_url=args.keycloak_url,
            realm=args.realm_name,
            admin_user=args.admin_user,
            admin_password=args.admin_password,
        )

        print(f"\n{'=' * 70}")
        print("Keycloak Realm Setup (OIDC Configuration)")
        print(f"{'=' * 70}\n")

        # 1. Create Realm
        admin.create_realm(args.realm_name, "NAK Planner")

        # 2. Create OIDC Public Client
        redirect_uris = [
            f"{args.frontend_url}/auth/callback",
        ]
        logout_redirect_uris = [
            args.frontend_url,
        ]

        client = admin.create_oidc_public_client(
            realm_name=args.realm_name,
            client_id=args.client_id,
            redirect_uris=redirect_uris,
            logout_redirect_uris=logout_redirect_uris,
        )

        # 3. Create Test User
        admin.create_user(
            realm_name=args.realm_name,
            username=args.test_user,
            email=args.test_email,
            password=args.test_password,
            first_name="Test",
            last_name="User",
        )

        # 4. Export Realm
        try:
            admin.export_realm(args.realm_name, args.output_file)
        except Exception as e:
            print(f"⚠ Realm export skipped: {e}")

        print(f"\n{'=' * 70}")
        print("✓ Setup Complete!")
        print(f"{'=' * 70}\n")

        # Display configuration info
        discovery_url = admin.get_oidc_discovery_url(args.realm_name)
        print("OIDC Discovery Configuration:")
        print(f"  Discovery URL: {discovery_url}")
        print(f"  Client ID:     {args.client_id}")
        print(f"  Realm:         {args.realm_name}")
        print(f"  Keycloak URL:  {args.keycloak_url}\n")

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
        print(f"4. Keycloak Admin: {args.keycloak_url}/admin/ (user: admin)\n")

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
