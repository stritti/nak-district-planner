# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Unit tests for scripts/ops/nakops.py (standard library only, no Docker)."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nakops  # noqa: E402


def run(argv: list[str], stdin: str = "") -> tuple[int, str]:
    out = io.StringIO()
    with unittest.mock.patch.object(sys, "stdin", io.StringIO(stdin)), redirect_stdout(out):
        code = nakops.main(argv)
    return code, out.getvalue()


class RedactTest(unittest.TestCase):
    def test_export_token_is_removed(self) -> None:
        line = 'INFO: 1.2.3.4:0 - "GET /api/v1/export/abc123/calendar.ics HTTP/1.1" 200'
        self.assertNotIn("abc123", nakops.redact(line))
        self.assertIn("/api/v1/export/[REDACTED]/calendar.ics", nakops.redact(line))

    def test_export_tokens_management_path_is_untouched(self) -> None:
        self.assertEqual(nakops.redact("GET /api/v1/export-tokens"), "GET /api/v1/export-tokens")

    def test_bearer_password_secret_and_email(self) -> None:
        text = (
            "Authorization: Bearer eyJhbGciOi.payload.sig password=hunter2 "
            'client_secret: "s3cr3t" VALKEY_PASSWORD=abc mail to anna.muster@example.org'
        )
        redacted = nakops.redact(text)
        for secret in ("eyJhbGciOi", "hunter2", "s3cr3t", "=abc", "anna.muster@example.org"):
            self.assertNotIn(secret, redacted)
        self.assertIn("[EMAIL]", redacted)

    def test_quoted_secret_with_spaces_is_masked_completely(self) -> None:
        text = '{"SMTP_PASSWORD": "alpha beta \\"gamma\\""} password=\'one two\' next'
        redacted = nakops.redact(text)
        for part in ("alpha", "beta", "gamma", "one", "two"):
            self.assertNotIn(part, redacted)
        self.assertIn("next", redacted)

    def test_password_only_url_credentials(self) -> None:
        redacted = nakops.redact("VALKEY_URL redis://:production-password@valkey:6379/0")
        self.assertNotIn("production-password", redacted)

    def test_url_credentials_and_oauth_parameters(self) -> None:
        text = "redis://user:pw@valkey:6379/0 /callback?code=xyz&state=abc&x=1"
        redacted = nakops.redact(text)
        self.assertNotIn(":pw@", redacted)
        self.assertNotIn("xyz", redacted)
        self.assertNotIn("state=abc", redacted)
        self.assertIn("x=1", redacted)

    def test_redact_command_copies_lines(self) -> None:
        code, out = run(["redact"], "a@b.de\nplain\n")
        self.assertEqual(code, 0)
        self.assertEqual(out, "[EMAIL]\nplain\n")


SAMPLE_LOGS = """\
backend-1  | 2026-11-05 08:00:00,123 ERROR [app.adapters.api.middleware.audit] Failed to build audit event (ValueError)
backend-1  | 2026-11-05 08:00:01,000 WARNING [app.adapters.api.middleware.rate_limit] Rate limit exceeded for 10.0.0.1 on GET /x (valkey)
backend-1  | INFO:     10.0.0.2:5000 - "GET /api/v1/export/topsecret/calendar.ics HTTP/1.1" 500 Internal Server Error
backend-1  | 2026-11-05 08:00:02,000 ERROR [app.x] mail to max@example.org failed for 0b7e7c1e-1111-2222-3333-444455556666
worker-1   | [2026-11-05 08:01:00,000: ERROR/ForkPoolWorker-1] Task sync_calendar_integration[0b7e7c1e-1111-2222-3333-444455556666] raised unexpected: TimeoutError()
worker-1   | [2026-11-05 08:01:05,000: INFO/MainProcess] Task sync_calendar_integration[0b7e7c1e-1111-2222-3333-444455556667] retry: Retry in 60s
db-1       | 2026-11-05 08:02:00.000 UTC [42] FATAL:  password authentication failed for user "nak_app"
traefik-1  | time="2026-11-05T08:03:00Z" level=error msg="backend unreachable"
frontend-1 | 10.0.0.3 - - [05/Nov/2026:08:00:00 +0000] "GET / HTTP/1.1" 200 512
"""


class AnalyzeLogsTest(unittest.TestCase):
    def test_counts_levels_and_events_per_service(self) -> None:
        summary = nakops.analyze(io.StringIO(SAMPLE_LOGS))
        self.assertEqual(summary.lines, 9)
        self.assertEqual(summary.levels["backend"]["ERROR"], 2)
        self.assertEqual(summary.levels["backend"]["WARNING"], 1)
        self.assertEqual(summary.levels["worker"]["ERROR"], 1)
        self.assertEqual(summary.levels["db"]["CRITICAL"], 1)
        self.assertEqual(summary.levels["traefik"]["ERROR"], 1)
        self.assertNotIn("frontend", summary.levels)
        for event in (
            "audit_failure",
            "rate_limit_exceeded",
            "http_5xx",
            "celery_task_failed",
            "celery_task_retry",
            "db_connection",
        ):
            self.assertEqual(summary.events[event], 1, event)

    def test_output_is_redacted_and_normalized(self) -> None:
        code, out = run(["analyze-logs", "--top", "20"], SAMPLE_LOGS)
        self.assertEqual(code, 0)
        self.assertNotIn("topsecret", out)
        self.assertNotIn("max@example.org", out)
        self.assertNotIn("0b7e7c1e", out)
        self.assertIn("<uuid>", out)

    def test_json_and_fail_on_errors(self) -> None:
        code, out = run(["analyze-logs", "--json", "--fail-on-errors"], SAMPLE_LOGS)
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["errors"], 5)
        self.assertNotIn("topsecret", out)

    def test_clean_logs_pass_fail_on_errors(self) -> None:
        code, _ = run(
            ["analyze-logs", "--fail-on-errors"], "backend-1  | 2026-11-05 08:00:00 INFO [x] ok\n"
        )
        self.assertEqual(code, 0)


def message(task: str) -> str:
    return json.dumps(
        {"body": "W1sic2VjcmV0Il0sIHt9XQ==", "headers": {"task": task, "argsrepr": "('a@b.de',)"}}
    )


class QueueHistogramTest(unittest.TestCase):
    def test_counts_task_names_without_arguments(self) -> None:
        stdin = "\n".join(
            [message("sync_calendar_integration")] * 2 + [message("check_version"), "garbage"]
        )
        code, out = run(["queue-histogram"], stdin)
        self.assertEqual(code, 0)
        self.assertIn("2  sync_calendar_integration", out)
        self.assertIn("(nicht lesbar)", out)
        self.assertNotIn("a@b.de", out)
        self.assertNotIn("W1sic2Vj", out)

    def test_mail_tasks_raise_a_warning(self) -> None:
        code, out = run(["queue-histogram"], message("dispatch_event_mail_hooks"))
        self.assertEqual(code, 1)
        self.assertIn("Mail", out)

    def test_unacked_entries_and_json(self) -> None:
        unacked = json.dumps([json.loads(message("check_version")), "", "celery"])
        code, out = run(["queue-histogram", "--json"], unacked)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["tasks"], {"check_version": 1})


class BackupsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def make(self, name: str, hours_ago: float) -> None:
        ts = (datetime.now(UTC) - timedelta(hours=hours_ago)).strftime("%Y%m%d_%H%M%S")
        (self.dir / name.format(ts=ts)).write_bytes(b"x" * 10)

    def test_stale_backup_is_a_finding(self) -> None:
        self.make("nak_planner_{ts}.dump.gpg", 30)
        self.make("nak_planner_{ts}.roles.sql.gpg", 30)
        code, out = run(
            ["backups", "--dir", str(self.dir), "--db", "nak_planner", "--max-age-hours", "26"]
        )
        self.assertEqual(code, 1)
        self.assertIn("BEFUND", out)

    def test_fresh_complete_backup_passes(self) -> None:
        self.make("nak_planner_{ts}.dump.gpg", 2)
        self.make("nak_planner_{ts}.roles.sql.gpg", 2)
        code, out = run(
            ["backups", "--dir", str(self.dir), "--db", "nak_planner", "--max-age-hours", "26"]
        )
        self.assertEqual(code, 0)
        self.assertIn("vollständig", out)

    def test_incomplete_pair_is_marked_and_does_not_count(self) -> None:
        self.make("nak_planner_{ts}.dump.gpg", 1)
        code, out = run(
            ["backups", "--dir", str(self.dir), "--db", "nak_planner", "--max-age-hours", "26"]
        )
        self.assertEqual(code, 1)
        self.assertIn("UNVOLLSTÄNDIG: Rollenarchiv fehlt", out)

    def test_empty_archive_does_not_count_as_complete(self) -> None:
        self.make("nak_planner_{ts}.dump.gpg", 1)
        self.make("nak_planner_{ts}.roles.sql.gpg", 1)
        next(self.dir.glob("*.roles.sql.gpg")).write_bytes(b"")
        code, out = run(
            ["backups", "--dir", str(self.dir), "--db", "nak_planner", "--max-age-hours", "26"]
        )
        self.assertEqual(code, 1)
        self.assertIn("UNVOLLSTÄNDIG: Rollenarchiv ist leer", out)
        code, _ = run(["backups", "--dir", str(self.dir), "--db", "nak_planner", "--latest-paths"])
        self.assertEqual(code, 1)

    def test_unencrypted_dump_is_marked(self) -> None:
        self.make("nak_planner_{ts}.dump", 1)
        self.make("nak_planner_{ts}.roles.sql", 1)
        _, out = run(["backups", "--dir", str(self.dir), "--db", "nak_planner"])
        self.assertIn("UNVERSCHLÜSSELT", out)

    def test_latest_paths(self) -> None:
        self.make("keycloak_{ts}.dump.gpg", 1)
        self.make("keycloak_{ts}.roles.sql.gpg", 1)
        code, out = run(["backups", "--dir", str(self.dir), "--db", "keycloak", "--latest-paths"])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertTrue(lines[0].endswith(".dump.gpg"))
        self.assertTrue(lines[1].endswith(".roles.sql.gpg"))
        code, _ = run(["backups", "--dir", str(self.dir), "--db", "nak_planner", "--latest-paths"])
        self.assertEqual(code, 1)


class EnvCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / ".env.example").write_text(
            "SECRET_KEY=replace-with-a-long-random-secret-key\nSMTP_PASSWORD=\nAPP_DB_PASSWORD=changeme\n"
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_env(self, content: str, *, group_readable: bool = False, name: str = ".env") -> None:
        """Create an env file 0600, or 0640 through the umask to exercise the permission check."""
        path = self.dir / name
        previous = os.umask(0o027 if group_readable else 0o077)
        try:
            path.write_text(content)
        finally:
            os.umask(previous)

    def test_clean_env_passes(self) -> None:
        self.write_env(
            "SECRET_KEY=" + "a" * 40 + "\nSMTP_PASSWORD=\nAPP_DB_PASSWORD=strong-value\n"
        )
        code, out = run(["env-check", "--dir", str(self.dir)])
        self.assertEqual(code, 0, out)

    def test_example_value_is_reported_without_value(self) -> None:
        self.write_env("SECRET_KEY=replace-with-a-long-random-secret-key\nAPP_DB_PASSWORD=strong\n")
        code, out = run(["env-check", "--dir", str(self.dir)])
        self.assertEqual(code, 1)
        self.assertIn("SECRET_KEY entspricht dem Beispielwert", out)
        self.assertNotIn("replace-with", out)

    def test_permissions_weak_values_owner_credentials_and_backup_key(self) -> None:
        self.write_env(
            "SECRET_KEY=xyz-long-enough\nAPP_DB_PASSWORD=changeme\nPOSTGRES_PASSWORD=owner\nAPP_ENV=production\n",
            group_readable=True,
        )
        code, out = run(["env-check", "--dir", str(self.dir)])
        self.assertEqual(code, 1)
        self.assertIn("Rechte 0640", out)
        self.assertIn("APP_DB_PASSWORD", out)
        self.assertIn("POSTGRES_PASSWORD gehört in .env.db", out)
        self.assertIn("BACKUP_ENCRYPT_KEY fehlt", out)
        self.assertNotIn("owner\n", out)

    def test_missing_required_secret_is_reported(self) -> None:
        self.write_env("SMTP_PASSWORD=\nAPP_DB_PASSWORD=strong\n")
        code, out = run(["env-check", "--dir", str(self.dir)])
        self.assertEqual(code, 1)
        self.assertIn("SECRET_KEY fehlt", out)
        self.assertNotIn("SMTP_PASSWORD", out)

    def test_other_env_files_are_checked(self) -> None:
        self.write_env("SECRET_KEY=" + "a" * 40 + "\n")
        (self.dir / ".env.keycloak.example").write_text("KC_BOOTSTRAP_ADMIN_PASSWORD=replace-me\n")
        self.write_env("KC_BOOTSTRAP_ADMIN_PASSWORD=replace-me\n", name=".env.keycloak")
        code, out = run(["env-check", "--dir", str(self.dir)])
        self.assertEqual(code, 1)
        self.assertIn(".env.keycloak: KC_BOOTSTRAP_ADMIN_PASSWORD", out)

    def test_removed_keycloak_bootstrap_password_is_not_missing(self) -> None:
        self.write_env("SECRET_KEY=" + "a" * 40 + "\n")
        (self.dir / ".env.keycloak.example").write_text(
            "KC_BOOTSTRAP_ADMIN_PASSWORD=replace-me\nKC_DB_PASSWORD=replace-me\n"
        )
        self.write_env("KC_DB_PASSWORD=" + "b" * 40 + "\n", name=".env.keycloak")
        _, out = run(["env-check", "--dir", str(self.dir)])
        self.assertNotIn("KC_BOOTSTRAP_ADMIN_PASSWORD", out)

    def test_missing_env_db_is_a_finding_in_production(self) -> None:
        self.write_env("APP_ENV=production\nBACKUP_ENCRYPT_KEY=ops@example.org\n")
        code, out = run(["env-check", "--dir", str(self.dir)])
        self.assertEqual(code, 1)
        self.assertIn(".env.db fehlt", out)
        self.assertNotIn(".env.keycloak fehlt", out)
        self.write_env("POSTGRES_PASSWORD=" + "c" * 40 + "\n", name=".env.db")
        code, out = run(["env-check", "--dir", str(self.dir)])
        self.assertNotIn(".env.db fehlt", out)

    def test_missing_env_db_is_fine_outside_production(self) -> None:
        self.write_env("APP_ENV=development\n")
        _, out = run(["env-check", "--dir", str(self.dir)])
        self.assertNotIn(".env.db fehlt", out)

    def test_missing_env_is_a_finding(self) -> None:
        code, _ = run(["env-check", "--dir", str(self.dir)])
        self.assertEqual(code, 1)


class SetEnvValueTest(unittest.TestCase):
    def test_replaces_active_line_and_drops_duplicates(self) -> None:
        lines = ["A=1", "# B=old", "A=2", "C=3"]
        self.assertEqual(nakops.set_env_value(lines, "A", "x"), ["A=x", "# B=old", "C=3"])

    def test_uncomments_example_line_in_place(self) -> None:
        self.assertEqual(nakops.set_env_value(["# B=old", "C=3"], "B", "y"), ["B=y", "C=3"])

    def test_appends_unknown_key(self) -> None:
        self.assertEqual(nakops.set_env_value(["C=3"], "D", "z"), ["C=3", "D=z"])


class ParserTest(unittest.TestCase):
    def test_usage_errors_do_not_echo_values(self) -> None:
        err = io.StringIO()
        with unittest.mock.patch.object(sys, "stderr", err), self.assertRaises(SystemExit) as ctx:
            nakops.main(["backups", "--dir", "x", "--db", "y", "--bogus", "s3cret"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertNotIn("s3cret", err.getvalue())


if __name__ == "__main__":
    unittest.main()
