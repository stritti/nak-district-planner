"""Static regression tests for docker-compose.prod.yml (Traefik + Keycloak + GHCR images)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]
PROD = "docker-compose.prod.yml"
APP_RUNTIME = ("backend", "worker", "beat", "frontend")
NON_PUBLIC = ("frontend", "backend", "worker", "beat", "db", "valkey", "keycloak", "keycloak-db")


def _compose() -> dict:
    return yaml.safe_load((REPO_ROOT / PROD).read_text(encoding="utf-8"))


def _services() -> dict:
    return _compose()["services"]


def _env_files(service: dict) -> list[str]:
    env_file = service.get("env_file", [])
    return [env_file] if isinstance(env_file, str) else list(env_file)


def _networks(service: dict) -> set[str]:
    networks = service.get("networks", [])
    return set(networks)  # list or mapping of network names


def _env_keys(filename: str) -> set[str]:
    keys = set()
    for line in (REPO_ROOT / filename).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            keys.add(stripped.partition("=")[0])
    return keys


def test_runtime_services_wait_for_the_one_shot_migration() -> None:
    services = _services()
    migrate = services["migrate"]
    assert migrate["command"] == "uv run alembic upgrade head"
    assert migrate["restart"] == "no"
    for name in APP_RUNTIME:
        assert services[name]["depends_on"]["migrate"] == {
            "condition": "service_completed_successfully"
        }, name


def test_secrets_reach_only_the_services_that_need_them() -> None:
    owners = {
        ".env.db": {"db", "migrate"},
        ".env.docker.migrate": {"migrate"},
        ".env.keycloak": {"keycloak"},
        ".env.keycloak-db": {"keycloak-db"},
    }
    for env_file, allowed in owners.items():
        users = {name for name, s in _services().items() if env_file in _env_files(s)}
        assert users == allowed, f"{env_file} is loaded by {sorted(users)}"

    for name in APP_RUNTIME:
        assert "environment" not in _services()[name], f"{name}: use env files"

    assert _env_keys(".env.keycloak.example") == {
        "KC_BOOTSTRAP_ADMIN_USERNAME",
        "KC_BOOTSTRAP_ADMIN_PASSWORD",
        "KC_DB_USERNAME",
        "KC_DB_PASSWORD",
    }
    assert _env_keys(".env.keycloak-db.example") == {
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    }
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env.keycloak" in gitignore
    assert ".env.keycloak-db" in gitignore


def test_application_runs_published_release_images_only() -> None:
    services = _services()
    for name, service in services.items():
        assert "build" not in service, f"{name} must not build on the server"
    for name in ("backend", "worker", "beat", "migrate", "frontend"):
        image = services[name]["image"]
        assert image.startswith("${IMAGE_REGISTRY:-ghcr.io/stritti/nak-district-planner}/"), name
        assert ":${APP_VERSION:?" in image, f"{name} must pin the release version"
        assert not image.endswith((":latest", ":main")), name


def test_only_traefik_is_published_and_no_container_gets_the_docker_socket() -> None:
    services = _services()
    assert services["traefik"]["ports"] == ["80:80", "443:443"]
    for name in NON_PUBLIC:
        assert "ports" not in services[name], f"{name} must not publish ports"
    for name, service in services.items():
        for volume in service.get("volumes", []):
            assert "docker.sock" not in str(volume), f"{name} mounts the Docker socket"
    assert any(arg.startswith("--providers.file.") for arg in services["traefik"]["command"]), (
        "routes must come from files, not the Docker provider"
    )
    assert not any("--providers.docker" in arg for arg in services["traefik"]["command"])


def test_databases_and_cache_sit_on_internal_networks_only() -> None:
    compose = _compose()
    services = compose["services"]
    assert compose["networks"]["data"]["internal"] is True
    assert compose["networks"]["idp"]["internal"] is True
    assert _networks(services["db"]) == {"data"}
    assert _networks(services["valkey"]) == {"data"}
    assert _networks(services["migrate"]) == {"data"}
    assert _networks(services["keycloak-db"]) == {"idp"}
    assert "data" not in _networks(services["frontend"])
    assert "data" not in _networks(services["traefik"])


def test_exactly_one_beat_scheduler_on_a_named_volume() -> None:
    compose = _compose()
    services = compose["services"]
    schedulers = [n for n, s in services.items() if " beat " in f" {s.get('command', '')} "]
    assert schedulers == ["beat"]
    beat = services["beat"]
    assert beat["deploy"]["replicas"] == 1
    volume = beat["volumes"][0].split(":")[0]
    assert volume in compose["volumes"]


def test_long_running_services_restart_and_are_hardened() -> None:
    for name, service in _services().items():
        assert "no-new-privileges:true" in service.get("security_opt", []), name
        if name != "migrate":
            assert service.get("restart") == "unless-stopped", name


def test_keycloak_trusts_forwarded_headers_only_from_the_proxy_network() -> None:
    compose = _compose()
    keycloak = compose["services"]["keycloak"]["environment"]
    assert keycloak["KC_PROXY_HEADERS"] == "xforwarded"
    edge_subnet = compose["networks"]["edge"]["ipam"]["config"][0]["subnet"]
    assert keycloak["KC_PROXY_TRUSTED_ADDRESSES"] == edge_subnet
    assert keycloak["KC_HOSTNAME"].startswith("https://")


def _routes(name: str) -> str:
    return (REPO_ROOT / "deploy" / "traefik" / "dynamic" / name).read_text(encoding="utf-8")


def test_keycloak_administration_is_behind_the_ip_allowlist() -> None:
    routes = _routes("keycloak.yml")
    admin_router = routes.split("auth-admin:", 1)[1].split("middlewares:", 2)
    assert "PathPrefix(`/admin`)" in admin_router[0]
    assert "PathPrefix(`/realms/master`)" in admin_router[0]
    assert "keycloak-admin-allowlist" in admin_router[1].splitlines()[0]
    assert 'env "KEYCLOAK_ADMIN_ALLOWED_IPS"' in routes
    assert "stsSeconds: 31536000" in _routes("app.yml")
    # Unset allowlist closes the admin console instead of opening it.
    traefik_env = _services()["traefik"]["environment"]
    assert (
        traefik_env["KEYCLOAK_ADMIN_ALLOWED_IPS"] == "${KEYCLOAK_ADMIN_ALLOWED_IPS:-127.0.0.1/32}"
    )


# --- Overrides for an existing Traefik / Keycloak (deploy/compose/) ----------


class _OverrideLoader(yaml.SafeLoader):
    """SafeLoader that accepts Compose merge tags (!override, !reset)."""


_OverrideLoader.add_multi_constructor(
    "!",
    lambda loader, _suffix, node: (
        loader.construct_sequence(node)
        if isinstance(node, yaml.SequenceNode)
        else loader.construct_mapping(node)
        if isinstance(node, yaml.MappingNode)
        else loader.construct_scalar(node)
    ),
)


def _override(name: str) -> dict:
    path = REPO_ROOT / "deploy" / "compose" / name
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_OverrideLoader)  # noqa: S506


def test_existing_keycloak_drops_the_bundled_keycloak_and_its_routes() -> None:
    raw = (REPO_ROOT / "deploy" / "compose" / "existing-keycloak.yml").read_text(encoding="utf-8")
    services = _override("existing-keycloak.yml")["services"]
    assert services["keycloak"]["profiles"] == ["bundled-keycloak"]
    assert services["keycloak-db"]["profiles"] == ["bundled-keycloak"]

    traefik = services["traefik"]
    assert "volumes: !override" in raw and "networks: !override" in raw
    assert not any("keycloak.yml" in v for v in traefik["volumes"])
    assert any(v.startswith("./deploy/traefik/dynamic/app.yml:") for v in traefik["volumes"])
    # No in-stack alias: AUTH_HOST must resolve to the real provider.
    assert all(not (cfg or {}).get("aliases") for cfg in traefik["networks"].values())
    assert "idp" not in services["backend"]["networks"]


def test_existing_traefik_publishes_through_labels_without_ports_or_socket() -> None:
    override = _override("existing-traefik.yml")
    services = override["services"]
    assert services["traefik"]["profiles"] == ["bundled-traefik"]
    assert override["networks"]["traefik-public"]["external"] is True

    for name in ("frontend", "keycloak"):
        service = services[name]
        assert "ports" not in service, name
        assert "volumes" not in service, name
        assert "traefik.enable=true" in service["labels"], name
        assert "traefik-public" in service["networks"], name

    labels = "\n".join(services["keycloak"]["labels"])
    admin_rule = next(
        line for line in services["keycloak"]["labels"] if "nak-auth-admin.rule=" in line
    )
    assert "PathPrefix(`/admin`)" in admin_rule
    assert "PathPrefix(`/realms/master`)" in admin_rule
    assert "nak-auth-admin.middlewares=nak-keycloak-admin" in labels
    assert "ipallowlist.sourcerange=${KEYCLOAK_ADMIN_ALLOWED_IPS:-127.0.0.1/32}" in labels
    assert "stsSeconds=31536000" in "\n".join(services["frontend"]["labels"])
