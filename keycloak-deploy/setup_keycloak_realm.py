#!/usr/bin/env python3
"""
Keycloak Realm Setup Script

Automatisiert den Setup eines Keycloak-Realms für NAK Planner:
- Erstellt Realm "nak-planner"
- Erstellt Client "nak-planner-api" (Confidential)
- Konfiguriert Redirect URIs
- Erstellt Test-User
- Exportiert Realm-Config

Requirements:
  - Python 3.11+
  - requests library (pip install requests)
  - Keycloak 26.5.6+ läuft und ist erreichbar

Usage:
    python3 setup_keycloak_realm.py --keycloak-url https://auth.5tritti.de \
        --admin-user admin --admin-password changeme
"""

import argparse
import json
import sys
import time
from typing import Any, Optional

import requests


class KeycloakAdminClient:
    """Minimal Keycloak Admin API client"""

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

        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()

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
        """Create a new realm"""
        print(f"Creating realm: {realm_name}...")
        url = f"{self.keycloak_url}/admin/realms"
        payload = {
            "realm": realm_name,
            "displayName": display_name or realm_name,
            "enabled": True,
            "sslRequired": "external",  # HTTPS only
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

    def create_client(
        self,
        realm_name: str,
        client_id: str,
        redirect_uris: list[str],
        logout_redirect_uris: Optional[list[str]] = None,
    ) -> dict:
        """Create a confidential client with redirect URIs"""
        print(f"Creating client: {client_id} in realm {realm_name}...")
        url = f"{self.keycloak_url}/admin/realms/{realm_name}/clients"

        payload = {
            "clientId": client_id,
            "name": client_id,
            "enabled": True,
            "public": False,  # Confidential
            "standardFlowEnabled": True,
            "implicitFlowEnabled": False,
            "directAccessGrantsEnabled": False,
            "redirectUris": redirect_uris,
            "webOrigins": ["+"],  # Allow all origins for now
            "protocolMappers": [],
        }

        if logout_redirect_uris:
            payload["attributes"] = {
                "post.logout.redirect.uris": " ".join(logout_redirect_uris)
            }

        response = requests.post(url, json=payload, headers=self._headers(), timeout=10)

        if response.status_code == 201:
            client_data = response.json()
            print(f"✓ Client created: {client_id}")
            return client_data
        elif response.status_code == 409:
            print(f"⚠ Client already exists: {client_id}")
            # Fetch existing client
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
        """Get client secret"""
        url = (
            f"{self.keycloak_url}/admin/realms/{realm_name}/clients/{client_uuid}"
            f"/client-secret"
        )
        response = requests.get(url, headers=self._headers(), timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["value"]

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


def main():
    parser = argparse.ArgumentParser(description="Setup Keycloak realm for NAK Planner")
    parser.add_argument(
        "--keycloak-url",
        required=True,
        help="Keycloak URL (e.g., https://auth.5tritti.de)",
    )
    parser.add_argument("--admin-user", default="admin", help="Keycloak admin username")
    parser.add_argument(
        "--admin-password",
        required=True,
        help="Keycloak admin password",
    )
    parser.add_argument("--realm-name", default="nak-planner", help="Realm name")
    parser.add_argument("--client-id", default="nak-planner-api", help="Client ID")
    parser.add_argument("--test-user", default="test", help="Test user username")
    parser.add_argument(
        "--test-password", default="test-password", help="Test user password"
    )
    parser.add_argument(
        "--test-email", default="test@example.com", help="Test user email"
    )
    parser.add_argument(
        "--frontend-url",
        default="https://planner.5tritti.de",
        help="Frontend URL for redirect URIs",
    )
    parser.add_argument(
        "--dev-url",
        default="http://localhost:3000",
        help="Dev frontend URL for redirect URIs",
    )
    parser.add_argument(
        "--output-file",
        default="keycloak-deploy/config/realm-export.json",
        help="Output file for realm export",
    )

    args = parser.parse_args()

    try:
        # Initialize admin client
        admin = KeycloakAdminClient(
            keycloak_url=args.keycloak_url,
            realm=args.realm_name,
            admin_user=args.admin_user,
            admin_password=args.admin_password,
        )

        print(f"\n{'=' * 60}\nKeycloak Realm Setup\n{'=' * 60}\n")

        # 1. Create Realm
        admin.create_realm(args.realm_name, "NAK Planner")

        # 2. Create Client
        redirect_uris = [
            f"{args.frontend_url}/auth/callback",
            f"{args.dev_url}/auth/callback",
        ]
        logout_redirect_uris = [
            args.frontend_url,
            args.dev_url,
        ]

        client = admin.create_client(
            realm_name=args.realm_name,
            client_id=args.client_id,
            redirect_uris=redirect_uris,
            logout_redirect_uris=logout_redirect_uris,
        )

        # Get client secret
        client_uuid = client.get("id")
        if client_uuid:
            client_secret = admin.get_client_secret(args.realm_name, client_uuid)
            print(f"\n{'=' * 60}")
            print(f"CLIENT SECRET (speichere in .env):")
            print(f"{'=' * 60}")
            print(f"{client_secret}\n")
        else:
            print("⚠ Could not retrieve client UUID, secret not printed")

        # 3. Create Test User
        admin.create_user(
            realm_name=args.realm_name,
            username=args.test_user,
            email=args.test_email,
            password=args.test_password,
        )

        # 4. Export Realm
        try:
            admin.export_realm(args.realm_name, args.output_file)
        except Exception as e:
            print(f"⚠ Realm export skipped: {e}")

        print(f"\n{'=' * 60}\n✓ Setup Complete!\n{'=' * 60}\n")
        print("Next steps:")
        print(
            f"1. Copy the CLIENT SECRET above to nak-district-planner/.env:\n"
            f"   KEYCLOAK_CLIENT_SECRET=<copied-secret>\n"
        )
        print(f"2. Test login at: https://auth.5tritti.de/")
        print(f"3. Update backend .env and start deployment\n")

    except KeyboardInterrupt:
        print("\n✗ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Setup failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
