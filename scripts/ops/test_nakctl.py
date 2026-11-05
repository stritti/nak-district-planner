# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Behaviour tests for scripts/ops/nakctl with a stubbed `docker`.

Valkey tests start a throwaway `redis-server`/`valkey-server` with a password and
are skipped when neither is installed. PostgreSQL tests run when
NAKCTL_TEST_PSQL_DSN points at a disposable database (CI sets it).
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import stat
import subprocess
import tempfile
import textwrap
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path

OPS_DIR = Path(__file__).resolve().parent
NAKCTL = OPS_DIR / "nakctl"

DOCKER_STUB = r"""#!/usr/bin/env bash
# Minimal docker stand-in: logs every call, answers from STUB_* variables.
printf '%s\n' "$*" >>"$STUB_LOG"
case "$1 $2" in
  "compose version") exit 0 ;;
  "info --format") echo "${STUB_DOCKER_ROOT:-/}"; exit 0 ;;
  "manifest inspect") [[ " ${STUB_MANIFESTS:-} " == *" ${3##*:} "* ]]; exit ;;
  "image ls") printf '%b' "${STUB_IMAGES:-}"; exit 0 ;;
  "image rm") exit 0 ;;
  "system df") exit 0 ;;
esac
if [[ "$1" == exec ]]; then
  case "$3" in
    true) exit 0 ;;
    pg_dump) echo "PGDMP"; exit 0 ;;
    pg_dumpall) echo "CREATE ROLE nak;"; exit 0 ;;
  esac
fi
if [[ "$1" == compose ]]; then
  shift
  case "$1" in
    ps)
      # ps --status running -q <service> | ps -q <service> | ps --format ...
      service="${*: -1}"
      if [[ " $* " == *" --status running "* ]]; then
        [[ " ${STUB_RUNNING:-} " == *" $service "* ]] && echo "cid-$service"
      elif [[ " $* " == *" -q "* ]]; then
        echo "cid-$service"
      fi
      exit 0 ;;
    exec)
      [[ " $* " == *" alembic heads"* ]] && { printf '%b' "${STUB_HEADS:-}"; exit 0; }
      exit "${STUB_EXEC_RC:-0}" ;;
    run)
      [[ " $* " == *" alembic heads"* ]] && { printf '%b' "${STUB_OLD_HEADS:-}"; exit 0; }
      exit 0 ;;
    pull | up | logs) [[ "$1" == logs ]] && printf '%b' "${STUB_LOGS:-}"; exit 0 ;;
  esac
fi
exit 0
"""

PSQL_STUB = r"""#!/usr/bin/env bash
cat >/dev/null
printf '%b' "${STUB_DB_REVS:-}"
"""


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class NakctlCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.deploy = self.root / "deploy"
        self.deploy.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "docker.log"
        self.log.touch()
        for name, content in (("docker", DOCKER_STUB), ("fakepsql", PSQL_STUB)):
            path = self.bin / name
            path.write_text(content)
            path.chmod(0o755)
        self.env_file = self.deploy / ".env"
        self.env_file.write_text("APP_VERSION=1.6.0\nPOSTGRES_DB=nak_planner\n")
        self.env_file.chmod(0o600)
        self.backups = self.root / "backups"
        self.env = {
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "HOME": str(self.root),
            "NAK_DEPLOY_DIR": str(self.deploy),
            "BACKUP_DIR": str(self.backups),
            "STUB_LOG": str(self.log),
            "STUB_DOCKER_ROOT": str(self.root),
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def nakctl(
        self, *args: str, stdin: str | None = "", **env: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(NAKCTL), *args],
            env={**self.env, **env},
            input=stdin,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    def docker_calls(self) -> list[str]:
        return self.log.read_text().splitlines()

    def audit_lines(self) -> list[str]:
        path = self.deploy / "logs" / "nakctl.log"
        return path.read_text().splitlines() if path.exists() else []


class CliTest(NakctlCase):
    def test_help_and_unknown_command(self) -> None:
        self.assertEqual(self.nakctl("--help").returncode, 0)
        result = self.nakctl("frobnicate")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Aufruf", result.stderr)

    def test_help_for_every_area(self) -> None:
        for area in (
            "status",
            "check",
            "queue",
            "backup",
            "logs",
            "deploy",
            "db",
            "superadmin",
            "cleanup",
        ):
            for argv in ((area, "--help"), (area, "-h"), ("help", area)):
                result = self.nakctl(*argv)
                self.assertEqual(result.returncode, 0, argv)
                self.assertIn(f"Aufruf: nakctl {area}", result.stdout, argv)
                self.assertIn("Beispiele:", result.stdout, argv)

    def test_help_on_a_command_shows_area_help_and_changes_nothing(self) -> None:
        result = self.nakctl("deploy", "update", "1.7.0", "--yes", "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--skip-backup", result.stdout)
        self.assertEqual(self.docker_calls(), [])

    def test_no_arguments_shows_overview(self) -> None:
        result = self.nakctl()
        self.assertEqual(result.returncode, 0)
        self.assertIn("Bereiche:", result.stdout)
        self.assertEqual(self.nakctl("help", "nope").returncode, 2)

    def test_unknown_subcommand_and_option(self) -> None:
        self.assertEqual(self.nakctl("queue", "explode").returncode, 2)
        self.assertEqual(self.nakctl("db", "stats", "--bogus").returncode, 2)

    def test_missing_docker_is_an_environment_error(self) -> None:
        (self.bin / "docker").unlink()
        result = self.nakctl("queue", "status", PATH=f"{self.bin}:/usr/bin:/bin")
        if shutil.which("docker", path="/usr/bin:/bin"):
            self.skipTest("a real docker is installed")
        self.assertEqual(result.returncode, 3)


class BackupTest(NakctlCase):
    def write_backup(self, db: str, hours_ago: float = 1) -> None:
        self.backups.mkdir(exist_ok=True)
        ts = datetime.fromtimestamp(time.time() - hours_ago * 3600, UTC).strftime("%Y%m%d_%H%M%S")
        for suffix in (".dump.gpg", ".roles.sql.gpg"):
            (self.backups / f"{db}_{ts}{suffix}").write_text("x")

    def hook(self, body: str, mode: int = 0o700) -> Path:
        path = self.deploy / "hook.sh"
        path.write_text("#!/usr/bin/env bash\n" + body)
        path.chmod(mode)
        return path

    def test_list_reports_stale_backup(self) -> None:
        self.write_backup("nak_planner", hours_ago=30)
        result = self.nakctl("backup", "list", "--max-age-hours", "26")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("BEFUND", result.stdout)

    def test_create_runs_post_hook_with_archive_paths(self) -> None:
        marker = self.root / "hook-args"
        self.hook(f'printf "%s\\n" "$@" > {marker}\n')
        result = self.nakctl("backup", "create", BACKUP_POST_HOOK="hook.sh")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        args = marker.read_text().splitlines()
        self.assertEqual(len(args), 2)
        self.assertTrue(args[0].endswith(".dump") and args[1].endswith(".roles.sql"))
        self.assertTrue(any("backup create" in line for line in self.audit_lines()))

    def test_failing_hook_keeps_backup_and_returns_finding(self) -> None:
        self.hook("exit 7\n")
        result = self.nakctl("backup", "create", BACKUP_POST_HOOK="hook.sh")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(len(list(self.backups.iterdir())), 2)
        self.assertIn("fehlgeschlagen", result.stdout)

    def test_group_writable_hook_is_not_run(self) -> None:
        marker = self.root / "ran"
        hook = self.hook(f"touch {marker}\n")
        hook.chmod(0o770)
        result = self.nakctl("backup", "create", BACKUP_POST_HOOK=str(hook))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(marker.exists())
        self.assertIn("schreibbar", result.stdout)

    def test_dry_run_creates_nothing(self) -> None:
        result = self.nakctl("backup", "create", "--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.backups.exists())


class DeployTest(NakctlCase):
    def test_unknown_version_changes_nothing(self) -> None:
        before = self.env_file.read_text()
        result = self.nakctl("deploy", "update", "9.9.9", "--yes", STUB_MANIFESTS="1.7.0")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("nicht veröffentlicht", result.stderr)
        self.assertEqual(self.env_file.read_text(), before)

    def test_invalid_version_is_a_usage_error(self) -> None:
        self.assertEqual(self.nakctl("deploy", "update", "latest").returncode, 2)

    def test_update_sets_version_and_remembers_previous(self) -> None:
        result = self.nakctl(
            "deploy", "update", "v1.7.0", "--yes", "--skip-backup", STUB_MANIFESTS="1.7.0"
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("APP_VERSION=1.7.0", self.env_file.read_text())
        self.assertEqual(stat.S_IMODE(self.env_file.stat().st_mode), 0o600)
        self.assertIn("PREVIOUS_VERSION=1.6.0", (self.deploy / "logs" / "nakctl.state").read_text())
        calls = self.docker_calls()
        self.assertTrue(any(c.startswith("compose run --no-deps --rm migrate") for c in calls))
        self.assertTrue(any(c == "compose up -d" for c in calls))

    def test_update_without_confirmation_is_aborted(self) -> None:
        result = self.nakctl("deploy", "update", "1.7.0", "--skip-backup", STUB_MANIFESTS="1.7.0")
        self.assertEqual(result.returncode, 4)
        self.assertIn("APP_VERSION=1.6.0", self.env_file.read_text())

    def _remember_previous(self, version: str = "1.5.0") -> None:
        (self.deploy / "logs").mkdir()
        (self.deploy / "logs" / "nakctl.state").write_text(f"PREVIOUS_VERSION={version}\n")

    def test_rollback_refuses_newer_schema(self) -> None:
        self._remember_previous()
        result = self.nakctl(
            "deploy",
            "rollback",
            "--yes",
            NAKCTL_PSQL=str(self.bin / "fakepsql"),
            STUB_DB_REVS="20261101_new\n",
            STUB_OLD_HEADS="20261001_old (head)\n",
        )
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("backup restore", result.stderr)
        self.assertIn("APP_VERSION=1.6.0", self.env_file.read_text())

    def test_rollback_with_matching_schema(self) -> None:
        self._remember_previous()
        result = self.nakctl(
            "deploy",
            "rollback",
            "--yes",
            NAKCTL_PSQL=str(self.bin / "fakepsql"),
            STUB_DB_REVS="20261001_old\n",
            STUB_OLD_HEADS="20261001_old (head)\n",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("APP_VERSION=1.5.0", self.env_file.read_text())
        self.assertIn("PREVIOUS_VERSION=1.6.0", (self.deploy / "logs" / "nakctl.state").read_text())


class CleanupTest(NakctlCase):
    def test_keeps_current_and_previous(self) -> None:
        (self.deploy / "logs").mkdir()
        (self.deploy / "logs" / "nakctl.state").write_text("PREVIOUS_VERSION=1.5.0\n")
        images = (
            "2026-10-01|ghcr.io/stritti/nak-district-planner/backend|1.4.0\\n"
            "2026-10-10|ghcr.io/stritti/nak-district-planner/backend|1.5.0\\n"
            "2026-10-20|ghcr.io/stritti/nak-district-planner/backend|1.6.0\\n"
        )
        result = self.nakctl("cleanup", "images", "--yes", STUB_IMAGES=images)
        self.assertEqual(result.returncode, 0, result.stderr)
        removals = [c for c in self.docker_calls() if c.startswith("image rm")]
        self.assertEqual(removals, ["image rm ghcr.io/stritti/nak-district-planner/backend:1.4.0"])

    def test_dry_run_removes_nothing(self) -> None:
        images = "2026-10-01|ghcr.io/stritti/nak-district-planner/backend|1.4.0\\n"
        result = self.nakctl("cleanup", "images", "--dry-run", STUB_IMAGES=images)
        self.assertEqual(result.returncode, 0)
        self.assertFalse(any(c.startswith("image rm") for c in self.docker_calls()))


class LogsAndSecretsTest(NakctlCase):
    LOGS = (
        'backend-1  | INFO:     1.2.3.4:0 - "GET /api/v1/export/abc123/calendar.ics HTTP/1.1" 500\\n'
        "backend-1  | 2026-11-05 08:00:00 ERROR [x] mail an eva@example.org\\n"
    )

    def test_analyze_redacts_and_fails_on_errors(self) -> None:
        result = self.nakctl(
            "logs", "analyze", "--since", "1h", "--fail-on-errors", STUB_LOGS=self.LOGS
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("abc123", result.stdout)
        self.assertNotIn("eva@example.org", result.stdout)
        self.assertIn("http_5xx", result.stdout)

    def test_export_writes_private_redacted_file(self) -> None:
        out = self.root / "export.log"
        result = self.nakctl("logs", "export", "--output", str(out), STUB_LOGS=self.LOGS)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o600)
        content = out.read_text()
        self.assertNotIn("abc123", content)
        self.assertNotIn("eva@example.org", content)

    def test_invalid_since_is_rejected(self) -> None:
        self.assertEqual(self.nakctl("logs", "analyze", "--since", "; rm -rf /").returncode, 2)

    def test_check_secrets_never_prints_values(self) -> None:
        (self.deploy / ".env.example").write_text(
            "SECRET_KEY=replace-with-a-long-random-secret-key\n"
        )
        self.env_file.write_text("SECRET_KEY=replace-with-a-long-random-secret-key\n")
        self.env_file.chmod(0o640)
        result = self.nakctl("check", "secrets")
        self.assertEqual(result.returncode, 1)
        self.assertIn("SECRET_KEY", result.stdout)
        self.assertNotIn("replace-with", result.stdout)


VALKEY_SERVER = shutil.which("valkey-server") or shutil.which("redis-server")
VALKEY_CLI = shutil.which("valkey-cli") or shutil.which("redis-cli")


@unittest.skipUnless(VALKEY_SERVER and VALKEY_CLI, "valkey-server/redis-server not installed")
class QueueTest(NakctlCase):
    PASSWORD = "test-valkey-password"

    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _free_port()
        cls.server = subprocess.Popen(
            [
                VALKEY_SERVER,
                "--port",
                str(cls.port),
                "--requirepass",
                cls.PASSWORD,
                "--save",
                "",
                "--appendonly",
                "no",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + 10
        while time.time() < deadline:
            if cls._cli_static("PING").strip() == "PONG":
                return
            time.sleep(0.1)
        raise RuntimeError("valkey test server did not start")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.terminate()
        cls.server.wait(timeout=10)

    @classmethod
    def _cli_static(cls, *args: str) -> str:
        return subprocess.run(
            [VALKEY_CLI, "-p", str(cls.port), *args],
            env={**os.environ, "REDISCLI_AUTH": cls.PASSWORD},
            capture_output=True,
            text=True,
            check=False,
        ).stdout

    def cli(self, *args: str) -> str:
        return self._cli_static(*args).strip()

    def setUp(self) -> None:
        super().setUp()
        self.cli("FLUSHALL")
        for task in (
            "sync_calendar_integration",
            "sync_calendar_integration",
            "dispatch_event_mail_hooks",
        ):
            body = json.dumps(
                {"body": "e30=", "headers": {"task": task, "argsrepr": "('x@y.de',)"}}
            )
            self.cli("RPUSH", "celery", body)
        self.cli(
            "HSET",
            "unacked",
            "tag1",
            json.dumps([{"headers": {"task": "check_version"}}, "", "celery"]),
        )
        self.cli("SET", "celery-task-meta-1", "{}")
        self.cli("SET", "celery-task-meta-2", "{}")
        self.cli("SET", "LIMITER/203.0.113.9/oidc", "3")
        self.env.update(
            NAKCTL_VALKEY_CLI=f"{VALKEY_CLI} -p {self.port}",
            REDISCLI_AUTH=self.PASSWORD,
        )

    def test_status_counts(self) -> None:
        result = self.nakctl("queue", "status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"Celery-Queue 'celery':\s+3")
        self.assertRegex(result.stdout, r"Unbestätigt \(unacked\):\s+1")
        self.assertRegex(result.stdout, r"Ergebnis-Schlüssel:\s+2")
        self.assertNotIn(self.PASSWORD, result.stdout + result.stderr)

    def test_inspect_shows_names_not_arguments(self) -> None:
        result = self.nakctl("queue", "inspect")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2  sync_calendar_integration", result.stdout)
        self.assertIn("Mail", result.stdout)
        self.assertNotIn("x@y.de", result.stdout)

    def test_purge_without_confirmation_changes_nothing(self) -> None:
        result = self.nakctl("queue", "purge", stdin=None)
        self.assertEqual(result.returncode, 4)
        self.assertEqual(self.cli("LLEN", "celery"), "3")

    def test_purge_dry_run_changes_nothing(self) -> None:
        result = self.nakctl("queue", "purge", "--dry-run")
        self.assertEqual(result.returncode, 0)
        self.assertIn("lösen Mails aus", result.stdout)
        self.assertEqual(self.cli("LLEN", "celery"), "3")

    def test_purge_keeps_rate_limit_keys(self) -> None:
        result = self.nakctl("queue", "purge", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.cli("LLEN", "celery"), "0")
        self.assertEqual(self.cli("GET", "LIMITER/203.0.113.9/oidc"), "3")
        self.assertEqual(self.cli("HLEN", "unacked"), "1")
        self.assertTrue(any("queue purge messages=3" in line for line in self.audit_lines()))

    def test_include_unacked_refused_while_worker_runs(self) -> None:
        result = self.nakctl("queue", "purge", "--include-unacked", "--yes", STUB_RUNNING="worker")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(self.cli("LLEN", "celery"), "3")

    def test_include_unacked_with_stopped_worker(self) -> None:
        result = self.nakctl("queue", "purge", "--include-unacked", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.cli("HLEN", "unacked"), "0")
        self.assertEqual(self.cli("GET", "LIMITER/203.0.113.9/oidc"), "3")

    def test_purge_results_only_touches_results(self) -> None:
        result = self.nakctl("queue", "purge-results", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.cli("EXISTS", "celery-task-meta-1"), "0")
        self.assertEqual(self.cli("LLEN", "celery"), "3")
        self.assertEqual(self.cli("GET", "LIMITER/203.0.113.9/oidc"), "3")

    def test_never_flushes(self) -> None:
        source = (OPS_DIR / "nakctl").read_text() + (OPS_DIR / "lib.sh").read_text()
        self.assertNotRegex(source, r"(?i)valkey_cli[^\n]*\bFLUSH(ALL|DB)\b")


PSQL_DSN = os.environ.get("NAKCTL_TEST_PSQL_DSN")


@unittest.skipUnless(PSQL_DSN and shutil.which("psql"), "NAKCTL_TEST_PSQL_DSN not set")
class DatabaseTest(NakctlCase):
    SCHEMA = textwrap.dedent(
        """
        DROP SCHEMA IF EXISTS nakctl_test CASCADE;
        CREATE SCHEMA nakctl_test;
        SET search_path = nakctl_test;
        CREATE TABLE users (sub text PRIMARY KEY, email text, is_superadmin boolean NOT NULL DEFAULT false,
                            created_at timestamptz NOT NULL DEFAULT now());
        CREATE TABLE app_superadmin_config (id int PRIMARY KEY, superadmin_sub text, bootstrap_completed_at timestamptz);
        INSERT INTO users VALUES ('old-sub', 'alt@example.org', true), ('new-sub', 'neu@example.org', false);
        INSERT INTO app_superadmin_config VALUES (1, 'old-sub', now());
        """
    )

    def psql(self, sql: str) -> str:
        return subprocess.run(
            ["psql", PSQL_DSN, "-X", "-tA", "-v", "ON_ERROR_STOP=1", "-c", sql],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "PGOPTIONS": "-c search_path=nakctl_test"},
        ).stdout.strip()

    def setUp(self) -> None:
        super().setUp()
        subprocess.run(
            ["psql", PSQL_DSN, "-X", "-q", "-v", "ON_ERROR_STOP=1"],
            input=self.SCHEMA,
            text=True,
            check=True,
        )
        self.env.update(NAKCTL_PSQL=f"psql {PSQL_DSN}", PGOPTIONS="-c search_path=nakctl_test")

    def tearDown(self) -> None:
        subprocess.run(
            ["psql", PSQL_DSN, "-X", "-q", "-c", "DROP SCHEMA IF EXISTS nakctl_test CASCADE"],
            check=False,
        )
        super().tearDown()

    def test_set_sub_rejects_unknown_subject(self) -> None:
        result = self.nakctl("superadmin", "set-sub", "nobody", "--yes")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.psql("SELECT superadmin_sub FROM app_superadmin_config"), "old-sub")

    def test_set_sub_updates_bootstrap(self) -> None:
        result = self.nakctl("superadmin", "set-sub", "new-sub", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.psql(
                "SELECT superadmin_sub || '|' || coalesce(bootstrap_completed_at::text, 'null') FROM app_superadmin_config"
            ),
            "new-sub|null",
        )

    def test_set_sub_quotes_input(self) -> None:
        result = self.nakctl("superadmin", "set-sub", "x'; DROP TABLE users; --", "--yes")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.psql("SELECT count(*) FROM users"), "2")

    def test_superadmin_list(self) -> None:
        result = self.nakctl("superadmin", "list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("old-sub", result.stdout)

    def test_stats_hide_literals_of_long_queries(self) -> None:
        sleeper = subprocess.Popen(
            ["psql", PSQL_DSN, "-X", "-c", "SELECT pg_sleep(6), 'geheim@example.org' AS mail"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(2.5)
            result = self.nakctl("db", "stats", "--long-seconds", "1")
        finally:
            sleeper.terminate()
            sleeper.wait(timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("pg_sleep", result.stdout)
        self.assertNotIn("geheim@example.org", result.stdout)
        self.assertIn("users", result.stdout)

    def test_vacuum_table(self) -> None:
        result = self.nakctl("db", "vacuum", "--table", "users", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.nakctl("db", "vacuum", "--table", "users;drop").returncode, 2)


if __name__ == "__main__":
    unittest.main()
