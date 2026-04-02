#!/usr/bin/env python3
"""
Authentik Blueprint Importer für NAK Planner OIDC

Dieses Script importiert den NAK Planner Blueprint in eine laufende Authentik-Instanz.

Requirements:
  - Python 3.11+
  - requests library (pip install requests)
  - Authentik 2024.4+ läuft und ist erreichbar

Usage:
    python3 import_blueprint.py \
        --authentik-url http://localhost:9000 \
        --token akadmin:insecure \
        --blueprint-file blueprint-nak-planner.yaml
        
    # Mit custom Werten:
    python3 import_blueprint.py \
        --authentik-url http://localhost:9000 \
        --token akadmin:insecure \
        --blueprint-file blueprint-nak-planner.yaml \
        --frontend-url http://localhost:5173 \
        --context frontend_url=http://localhost:5173
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Optional

import requests
import yaml


class AuthentikBlueprintImporter:
    """Authentik Blueprint importer for NAK Planner setup"""

    def __init__(self, authentik_url: str, token: str):
        self.authentik_url = authentik_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict:
        """Authorization headers"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _headers_yaml(self) -> dict:
        """Authorization headers for YAML"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/yaml",
        }

    def health_check(self) -> bool:
        """Check if Authentik is running"""
        try:
            url = f"{self.authentik_url}/-/health/live/"
            response = requests.get(url, timeout=5)
            return response.status_code == 204
        except requests.exceptions.RequestException as e:
            print(f"Health check failed: {e}")
            return False

    def wait_for_authentik(self, max_retries: int = 30) -> bool:
        """Wait for Authentik to be ready"""
        print("Waiting for Authentik to be ready...\n")

        for attempt in range(max_retries):
            if self.health_check():
                print("✓ Authentik is ready\n")
                return True

            print(
                f"  Attempt {attempt + 1}/{max_retries}: Waiting for Authentik...",
                end="\r",
            )
            time.sleep(2)

        print(f"\n✗ Authentik did not become ready after {max_retries * 2} seconds")
        return False

    def get_token_from_credentials(self, username: str, password: str) -> Optional[str]:
        """Get API token from credentials (username:password)"""
        print("Authenticating with Authentik...")

        url = f"{self.authentik_url}/api/v3/core/tokens/"

        # First, get session token
        headers = {
            "Content-Type": "application/json",
        }

        # Try to use basic auth
        auth = (username, password)

        try:
            response = requests.post(
                url,
                json={"identifier": username, "description": "Blueprint Import"},
                auth=auth,
                headers=headers,
                timeout=10,
            )

            if response.status_code == 201:
                token_data = response.json()
                token = token_data.get("token")
                print(f"✓ Authentication successful\n")
                return token
            else:
                print(
                    f"✗ Authentication failed: {response.status_code} {response.text}"
                )
                return None
        except Exception as e:
            print(f"✗ Authentication error: {e}")
            return None

    def import_blueprint(
        self,
        blueprint_content: str,
        blueprint_name: str,
        context_overrides: Optional[dict] = None,
    ) -> bool:
        """Import blueprint YAML"""
        print(f"Importing blueprint: {blueprint_name}...\n")

        try:
            # Parse YAML
            blueprint_data = yaml.safe_load(blueprint_content)

            # Apply context overrides
            if context_overrides:
                if "context" not in blueprint_data:
                    blueprint_data["context"] = {}
                blueprint_data["context"].update(context_overrides)

            # Convert back to YAML
            blueprint_yaml = yaml.dump(blueprint_data)

            # Create blueprint instance
            url = f"{self.authentik_url}/api/v3/blueprints/instances/"

            payload = {
                "name": blueprint_name,
                "content": blueprint_yaml,
                "enabled": True,
                "labels": {
                    "app": "nak-planner",
                },
            }

            response = requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=30,
            )

            if response.status_code == 201:
                blueprint_obj = response.json()
                print(f"✓ Blueprint imported successfully")
                print(f"  Blueprint ID: {blueprint_obj.get('pk')}")
                return True
            elif response.status_code == 400:
                # Might already exist
                error = response.json()
                if "name" in error and "already exists" in str(error):
                    print(f"⚠ Blueprint already exists, updating...")
                    return self.update_blueprint(blueprint_yaml, blueprint_name)
                else:
                    print(f"✗ Blueprint import failed: {error}")
                    return False
            else:
                print(f"✗ Blueprint import failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except yaml.YAMLError as e:
            print(f"✗ YAML parsing error: {e}")
            return False
        except Exception as e:
            print(f"✗ Blueprint import error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def update_blueprint(self, blueprint_yaml: str, blueprint_name: str) -> bool:
        """Update existing blueprint"""
        # Get blueprint by name
        url = f"{self.authentik_url}/api/v3/blueprints/instances/?name={blueprint_name}"

        try:
            response = requests.get(url, headers=self._headers(), timeout=10)
            response.raise_for_status()

            data = response.json()
            if not data.get("results"):
                print(f"✗ Blueprint not found: {blueprint_name}")
                return False

            blueprint_id = data["results"][0]["pk"]

            # Update blueprint
            update_url = (
                f"{self.authentik_url}/api/v3/blueprints/instances/{blueprint_id}/"
            )

            payload = {
                "name": blueprint_name,
                "content": blueprint_yaml,
                "enabled": True,
            }

            response = requests.patch(
                update_url,
                json=payload,
                headers=self._headers(),
                timeout=30,
            )

            if response.status_code == 200:
                print(f"✓ Blueprint updated successfully")
                return True
            else:
                print(f"✗ Blueprint update failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"✗ Blueprint update error: {e}")
            return False

    def apply_blueprint(self, blueprint_id: int) -> bool:
        """Apply/execute blueprint"""
        print(f"Applying blueprint...\n")

        url = f"{self.authentik_url}/api/v3/blueprints/instances/{blueprint_id}/apply/"

        try:
            response = requests.post(
                url,
                headers=self._headers(),
                timeout=30,
            )

            if response.status_code in [200, 204]:
                print(f"✓ Blueprint applied successfully")
                return True
            else:
                print(f"✗ Blueprint apply failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False

        except Exception as e:
            print(f"✗ Blueprint apply error: {e}")
            return False

    def list_blueprints(self) -> bool:
        """List all blueprints"""
        print("Listing blueprints...\n")

        url = f"{self.authentik_url}/api/v3/blueprints/instances/"

        try:
            response = requests.get(url, headers=self._headers(), timeout=10)
            response.raise_for_status()

            data = response.json()
            blueprints = data.get("results", [])

            if not blueprints:
                print("No blueprints found")
                return True

            print(f"Found {len(blueprints)} blueprint(s):")
            for bp in blueprints:
                print(f"  - {bp['name']} (ID: {bp['pk']}, Enabled: {bp['enabled']})")

            return True

        except Exception as e:
            print(f"✗ Failed to list blueprints: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Import Authentik Blueprint for NAK Planner"
    )
    parser.add_argument(
        "--authentik-url",
        required=True,
        help="Authentik URL (e.g., http://localhost:9000)",
    )
    parser.add_argument(
        "--token",
        help="API Token or username:password for authentication",
    )
    parser.add_argument(
        "--blueprint-file",
        default="blueprint-nak-planner.yaml",
        help="Blueprint YAML file path",
    )
    parser.add_argument(
        "--blueprint-name",
        default="NAK Planner OIDC Blueprint",
        help="Blueprint name in Authentik",
    )
    parser.add_argument(
        "--context",
        action="append",
        nargs=2,
        metavar=("KEY", "VALUE"),
        help="Override blueprint context values (can be used multiple times)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply blueprint after import",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing blueprints and exit",
    )

    args = parser.parse_args()

    try:
        # Initialize importer
        importer = AuthentikBlueprintImporter(
            authentik_url=args.authentik_url,
            token=args.token or "akadmin:insecure",
        )

        print(f"{'=' * 70}")
        print("Authentik Blueprint Importer")
        print(f"{'=' * 70}\n")

        # Wait for Authentik
        if not importer.wait_for_authentik():
            sys.exit(1)

        # List blueprints if requested
        if args.list:
            importer.list_blueprints()
            sys.exit(0)

        # Read blueprint file
        blueprint_path = Path(args.blueprint_file)
        if not blueprint_path.exists():
            print(f"✗ Blueprint file not found: {args.blueprint_file}")
            sys.exit(1)

        with open(blueprint_path, "r") as f:
            blueprint_content = f.read()

        # Parse context overrides
        context_overrides = {}
        if args.context:
            for key, value in args.context:
                context_overrides[key] = value

        # Import blueprint
        if not importer.import_blueprint(
            blueprint_content=blueprint_content,
            blueprint_name=args.blueprint_name,
            context_overrides=context_overrides,
        ):
            sys.exit(1)

        # Apply blueprint if requested
        if args.apply:
            print("\n" + "=" * 70)
            # Get blueprint ID
            url = f"{args.authentik_url}/api/v3/blueprints/instances/?name={args.blueprint_name}"
            response = requests.get(
                url,
                headers=importer._headers(),
                timeout=10,
            )
            data = response.json()
            if data.get("results"):
                blueprint_id = data["results"][0]["pk"]
                importer.apply_blueprint(blueprint_id)

        print(f"\n{'=' * 70}")
        print("✓ Import Complete!")
        print(f"{'=' * 70}\n")

        print("Next steps:")
        print(f"1. Visit Authentik admin: {args.authentik_url}/if/admin/")
        print(f"2. Navigate to System → Blueprints")
        print(f"3. Verify '{args.blueprint_name}' is enabled")
        print(f"4. Configure test user password if needed")
        print(f"5. Test OIDC flow: http://localhost:5173/login\n")

    except KeyboardInterrupt:
        print("\n✗ Import cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Import failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
