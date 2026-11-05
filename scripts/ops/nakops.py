#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Helpers for scripts/ops/nakctl that are easier to get right (and test) in Python.

Standard library only: the production host needs nothing but Python 3.
Subcommands:

  analyze-logs     summarise `docker compose logs` output from stdin (redacted)
  redact           copy stdin to stdout with secrets and e-mail addresses masked
  queue-histogram  count Celery task names in raw queue messages from stdin
  backups          list backup archives, pair database/role archives, check age
  env-check        check .env files: permissions, placeholders, owner credentials
  init-env         create missing .env files from their templates with fresh secrets

Exit codes follow nakctl: 0 ok, 1 finding, 2 usage error, 3 environment unusable.
No subcommand ever prints a secret value.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import stat
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

EXIT_OK = 0
EXIT_FINDING = 1
EXIT_USAGE = 2
EXIT_ENV = 3

REDACTED = "[REDACTED]"

# --------------------------------------------------------------------------- redaction

_SECRET_WORDS = r"(?:password|passwd|secret|token|api[_-]?key|credential|authorization|cookie)"

_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    # ICS export feed: everything below /export/ is the bearer secret
    # (mirrors app/adapters/api/log_redaction.py; `export-tokens` is untouched).
    (re.compile(r"(/export/)[^/?#\s\"']+"), rf"\1{REDACTED}"),
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+"), rf"\1 {REDACTED}"),
    # Credentials embedded in URLs: scheme://user:password@host
    (re.compile(r"(://)[^/\s:@]*:[^/\s@]+@"), rf"\1{REDACTED}@"),
    # key=value / key: value / "key": "value" for secret-looking keys; quoted values
    # (with spaces or escapes) are masked as a whole first.
    (
        re.compile(rf"(?i)(\b[\w-]*{_SECRET_WORDS}[\w-]*[\"']?\s*[=:]\s*)\"(?:[^\"\\\n]|\\.)*\""),
        rf'\1"{REDACTED}"',
    ),
    (
        re.compile(rf"(?i)(\b[\w-]*{_SECRET_WORDS}[\w-]*[\"']?\s*[=:]\s*)'(?:[^'\\\n]|\\.)*'"),
        rf"\1'{REDACTED}'",
    ),
    (
        re.compile(rf"(?i)(\b[\w-]*{_SECRET_WORDS}[\w-]*[\"']?\s*[=:]\s*[\"']?)[^\s\"'&,;}}]+"),
        rf"\1{REDACTED}",
    ),
    # OAuth callback parameters
    (re.compile(r"(?i)([?&](?:code|state|session_state)=)[^&\s\"']+"), rf"\1{REDACTED}"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
)


def redact(text: str) -> str:
    """Mask export tokens, bearer tokens, passwords, secrets and e-mail addresses."""
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


# ----------------------------------------------------------------------- log analysis

_COMPOSE_PREFIX = re.compile(r"^(?P<service>[A-Za-z0-9_.-]+?)(?:-\d+)?\s+\|\s?(?P<message>.*)$")
_LEVEL = re.compile(
    r"\b(CRITICAL|FATAL|PANIC|ERROR|WARNING|WARN)\b|\blevel=(fatal|panic|error|warn(?:ing)?)\b"
)
_LEVEL_NAMES = {
    "critical": "CRITICAL",
    "fatal": "CRITICAL",
    "panic": "CRITICAL",
    "error": "ERROR",
    "warning": "WARNING",
    "warn": "WARNING",
}

# Named detectors for operationally relevant events. Unknown errors still show up
# in the per-service level counts and in the top messages.
PATTERNS: dict[str, re.Pattern[str]] = {
    "http_5xx": re.compile(r"\"[A-Z]+ [^\"]* HTTP/[0-9.]+\" 5\d\d\b"),
    "celery_task_failed": re.compile(r"Task [\w.]+\[[0-9a-f-]+\] raised unexpected"),
    "celery_task_retry": re.compile(r"Task [\w.]+\[[0-9a-f-]+\] retry: |Retry in \d+(?:\.\d+)?s"),
    "celery_time_limit": re.compile(
        r"(?:Hard|Soft) time limit|SoftTimeLimitExceeded|TimeLimitExceeded"
    ),
    "rate_limit_fallback": re.compile(r"(?i)local fallback|fail[- ]open"),
    "rate_limit_exceeded": re.compile(r"Rate limit exceeded"),
    "audit_failure": re.compile(
        r"(?i)audit (?:event|entry|log)[^\n]*(?:fail|error)|failed to (?:build|write|persist) audit"
    ),
    "db_connection": re.compile(
        r"(?i)password authentication failed|could not connect to server|connection refused|"
        r"too many connections|remaining connection slots"
    ),
    "schema_mismatch": re.compile(
        r"SchemaVersionError|database schema is not current|alembic head", re.IGNORECASE
    ),
    "valkey_connection": re.compile(
        r"(?i)(?:redis|valkey)[^\n]*(?:connection|timeout)[^\n]*(?:error|refused|lost)"
    ),
}

_NORMALIZE: tuple[tuple[re.Pattern[str], str], ...] = (
    # Leading timestamps of the backend, Celery and PostgreSQL formats
    (
        re.compile(
            r"^\[?\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2}| UTC)?(?::|\])?\s*"
        ),
        "",
    ),
    (
        re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
        "<uuid>",
    ),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), "<ip>"),
    (re.compile(r"\b[0-9a-f]{12,}\b", re.I), "<hex>"),
    (re.compile(r"\b\d+(?:\.\d+)?\b"), "<n>"),
)

_MAX_MESSAGE = 160


def _normalize(message: str) -> str:
    message = redact(message.strip())
    for pattern, replacement in _NORMALIZE:
        message = pattern.sub(replacement, message)
    if len(message) > _MAX_MESSAGE:
        message = message[: _MAX_MESSAGE - 1] + "…"
    return message


def _level(message: str) -> str | None:
    match = _LEVEL.search(message)
    if not match:
        return None
    return _LEVEL_NAMES[(match.group(1) or match.group(2)).lower()]


@dataclass
class LogSummary:
    lines: int = 0
    levels: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    events: Counter[str] = field(default_factory=Counter)
    events_by_service: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    top: Counter[tuple[str, str, str]] = field(default_factory=Counter)

    @property
    def error_count(self) -> int:
        return sum(c["ERROR"] + c["CRITICAL"] for c in self.levels.values())

    def to_dict(self, top_n: int) -> dict[str, object]:
        return {
            "lines": self.lines,
            "levels": {svc: dict(counts) for svc, counts in sorted(self.levels.items())},
            "events": dict(sorted(self.events.items())),
            "events_by_service": {
                svc: dict(c) for svc, c in sorted(self.events_by_service.items())
            },
            "top_messages": [
                {"service": svc, "level": lvl, "message": msg, "count": n}
                for (svc, lvl, msg), n in self.top.most_common(top_n)
            ],
            "errors": self.error_count,
        }


def analyze(lines: list[str] | object) -> LogSummary:
    summary = LogSummary()
    for raw in lines:  # type: ignore[attr-defined]
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        summary.lines += 1
        match = _COMPOSE_PREFIX.match(line)
        service, message = (
            (match.group("service"), match.group("message")) if match else ("-", line)
        )
        level = _level(message)
        if level:
            summary.levels[service][level] += 1
            summary.top[(service, level, _normalize(message))] += 1
        for name, pattern in PATTERNS.items():
            if pattern.search(message):
                summary.events[name] += 1
                summary.events_by_service[service][name] += 1
    return summary


def _print_summary(summary: LogSummary, top_n: int) -> None:
    print(f"Ausgewertete Zeilen: {summary.lines}")
    print()
    print("Warnungen und Fehler je Dienst:")
    if not summary.levels:
        print("  keine")
    for service, counts in sorted(summary.levels.items()):
        parts = ", ".join(
            f"{lvl} {counts[lvl]}" for lvl in ("CRITICAL", "ERROR", "WARNING") if counts[lvl]
        )
        print(f"  {service:<14} {parts}")
    print()
    print("Erkannte Ereignisse:")
    if not summary.events:
        print("  keine")
    for name, count in sorted(summary.events.items()):
        services = ", ".join(
            f"{svc} {c[name]}" for svc, c in sorted(summary.events_by_service.items()) if c[name]
        )
        print(f"  {name:<22} {count:>6}  ({services})")
    if summary.top:
        print()
        print(f"Häufigste Meldungen (Top {top_n}, redigiert):")
        for (service, level, message), count in summary.top.most_common(top_n):
            print(f"  {count:>6}  {service:<10} {level:<8} {message}")


def cmd_analyze_logs(args: argparse.Namespace) -> int:
    summary = analyze(sys.stdin)
    if args.json:
        json.dump(summary.to_dict(args.top), sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        _print_summary(summary, args.top)
    if args.fail_on_errors and summary.error_count:
        return EXIT_FINDING
    return EXIT_OK


def cmd_redact(_args: argparse.Namespace) -> int:
    for line in sys.stdin:
        sys.stdout.write(redact(line))
    return EXIT_OK


# ------------------------------------------------------------------------ queue

# Tasks whose loss means a mail is never sent (non-idempotent, never replayed).
MAIL_TASKS = frozenset({"dispatch_event_mail_hooks", "check_due_reminders", "scan_slot_gaps"})


def queue_histogram(lines: list[str] | object) -> tuple[Counter[str], int]:
    """Count task names of raw Kombu/Celery messages; arguments are never decoded."""
    counts: Counter[str] = Counter()
    unreadable = 0
    for raw in lines:  # type: ignore[attr-defined]
        raw = raw.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
        except ValueError:
            unreadable += 1
            continue
        if isinstance(message, list) and message:
            # unacked hash values are [message, exchange, routing_key]
            message = message[0]
        task = None
        if isinstance(message, dict):
            headers = message.get("headers")
            if isinstance(headers, dict):
                task = headers.get("task")
        if isinstance(task, str) and re.fullmatch(r"[\w.:-]{1,200}", task):
            counts[task] += 1
        else:
            unreadable += 1
    return counts, unreadable


def cmd_queue_histogram(args: argparse.Namespace) -> int:
    counts, unreadable = queue_histogram(sys.stdin)
    mail = sum(n for task, n in counts.items() if task.rsplit(".", 1)[-1] in MAIL_TASKS)
    if args.json:
        json.dump(
            {"tasks": dict(counts), "unreadable": unreadable, "mail_tasks": mail},
            sys.stdout,
            indent=2,
        )
        print()
    else:
        if not counts and not unreadable:
            print("  (keine Nachrichten)")
        for task, n in counts.most_common():
            marker = "  ← Mail" if task.rsplit(".", 1)[-1] in MAIL_TASKS else ""
            print(f"  {n:>6}  {task}{marker}")
        if unreadable:
            print(f"  {unreadable:>6}  (nicht lesbar)")
        if mail:
            print()
            print(
                f"WARNUNG: {mail} Nachricht(en) lösen Mails aus. Nach dem Leeren werden diese Mails nie versendet."
            )
    return EXIT_FINDING if mail else EXIT_OK


# ---------------------------------------------------------------------- backups

_BACKUP_NAME = re.compile(
    r"^(?P<db>.+)_(?P<ts>\d{8}_\d{6})\.(?P<kind>dump|roles\.sql)(?P<gpg>\.gpg)?$"
)


@dataclass
class BackupSet:
    database: str
    timestamp: datetime
    dump: Path | None = None
    roles: Path | None = None

    @property
    def problem(self) -> str | None:
        """Why the set is not usable, or None. A failed run can leave an empty archive."""
        if self.roles is None:
            return "Rollenarchiv fehlt"
        if self.dump is None:
            return "Datenbankarchiv fehlt"
        if self.dump.stat().st_size == 0:
            return "Datenbankarchiv ist leer"
        if self.roles.stat().st_size == 0:
            return "Rollenarchiv ist leer"
        return None

    @property
    def complete(self) -> bool:
        return self.problem is None

    @property
    def size(self) -> int:
        return sum(p.stat().st_size for p in (self.dump, self.roles) if p is not None)


def collect_backups(directory: Path) -> list[BackupSet]:
    sets: dict[tuple[str, str], BackupSet] = {}
    if not directory.is_dir():
        return []
    for path in directory.iterdir():
        match = _BACKUP_NAME.match(path.name)
        if not match or not path.is_file():
            continue
        key = (match["db"], match["ts"])
        entry = sets.setdefault(
            key, BackupSet(match["db"], datetime.strptime(match["ts"], "%Y%m%d_%H%M%S"))
        )
        if match["kind"] == "dump":
            entry.dump = path
        else:
            entry.roles = path
    return sorted(sets.values(), key=lambda s: (s.database, s.timestamp), reverse=True)


def _human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def _utcnow() -> datetime:
    """scripts/backup.sh names archives with a UTC timestamp (`date -u`)."""
    return datetime.now(UTC).replace(tzinfo=None)


def _age_hours(entry: BackupSet, now: datetime) -> float:
    return (now - entry.timestamp).total_seconds() / 3600


def cmd_backups(args: argparse.Namespace) -> int:
    directory = Path(args.dir)
    now = _utcnow()
    sets = collect_backups(directory)
    if args.latest_paths:
        for entry in sets:
            if entry.database == args.db and entry.complete:
                print(entry.dump)
                print(entry.roles)
                return EXIT_OK
        print(f"Kein vollständiges Backup für '{args.db}' in {directory}", file=sys.stderr)
        return EXIT_FINDING
    if not args.quiet:
        if not sets:
            print(f"Keine Backups in {directory}")
        else:
            print(f"{'Datenbank':<16} {'Zeitpunkt (UTC)':<19} {'Alter':>8} {'Größe':>9}  Status")
        for entry in sets:
            problem = entry.problem
            status = "vollständig" if problem is None else f"UNVOLLSTÄNDIG: {problem}"
            encrypted = (
                "" if entry.dump is None or entry.dump.suffix == ".gpg" else " (UNVERSCHLÜSSELT)"
            )
            print(
                f"{entry.database:<16} {entry.timestamp:%Y-%m-%d %H:%M:%S} {_age_hours(entry, now):>7.1f}h "
                f"{_human_size(entry.size):>9}  {status}{encrypted}"
            )
    if args.max_age_hours is None:
        return EXIT_OK
    fresh = [
        e
        for e in sets
        if e.database == args.db and e.complete and _age_hours(e, now) <= args.max_age_hours
    ]
    if fresh:
        if args.quiet:
            print(
                f"Backup: jüngstes vollständiges Backup von '{args.db}' ist {_age_hours(fresh[0], now):.1f} h alt"
            )
        return EXIT_OK
    print(
        f"BEFUND: kein vollständiges Backup von '{args.db}' jünger als {args.max_age_hours:g} h in {directory}",
    )
    return EXIT_FINDING


# -------------------------------------------------------------------- env check

_SECRET_KEY_NAME = re.compile(r"(PASSWORD|SECRET|_KEY$|TOKEN)")
_WEAK_VALUES = frozenset({"changeme", "change-me", "password", "default", "secret", "admin"})
# Owner credentials must live in .env.db only (app/config.py::production_guard).
_OWNER_ONLY = ("POSTGRES_PASSWORD", "MIGRATION_DATABASE_URL")
# Removed from .env.keycloak once a permanent admin exists (production-compose.md).
_REMOVABLE_SECRETS = frozenset({"KC_BOOTSTRAP_ADMIN_PASSWORD"})


def parse_env(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines without executing anything; later keys win like Compose."""
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def check_env_file(path: Path, example: Path | None, *, runtime: bool) -> list[str]:
    """Return findings for one env file. Findings name keys, never values."""
    findings: list[str] = []
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        findings.append(f"{path.name}: Rechte {mode:04o}, erwartet 0600 (chmod 600 {path.name})")
    values = parse_env(path)
    examples = parse_env(example) if example is not None and example.is_file() else {}
    for key, value in sorted(values.items()):
        if not _SECRET_KEY_NAME.search(key):
            continue
        example_value = examples.get(key)
        if value and example_value and value == example_value:
            findings.append(f"{path.name}: {key} entspricht dem Beispielwert")
        elif value.strip().lower() in _WEAK_VALUES:
            findings.append(f"{path.name}: {key} hat einen Standardwert")
        elif not value and example_value:
            findings.append(f"{path.name}: {key} ist leer")
    # Secrets the example sets (e.g. SECRET_KEY, VALKEY_PASSWORD) must exist;
    # those with an empty example value (e.g. SMTP_PASSWORD) are optional, and
    # temporary bootstrap credentials are removed after setup by design.
    for key, example_value in sorted(examples.items()):
        if key in _REMOVABLE_SECRETS:
            continue
        if _SECRET_KEY_NAME.search(key) and example_value and key not in values:
            findings.append(f"{path.name}: {key} fehlt")
    if runtime:
        for key in _OWNER_ONLY:
            if values.get(key):
                findings.append(
                    f"{path.name}: {key} gehört in .env.db, nicht in die Laufzeit-Umgebung"
                )
        if values.get("APP_ENV") == "production" and not values.get("BACKUP_ENCRYPT_KEY"):
            findings.append(f"{path.name}: BACKUP_ENCRYPT_KEY fehlt (Pflicht in Produktion)")
    return findings


_REQUIRED_IN_PRODUCTION = frozenset({".env.db"})

ENV_FILES = (
    (".env", ".env.example", True),
    (".env.db", ".env.db.example", False),
    (".env.keycloak", ".env.keycloak.example", False),
    (".env.keycloak-db", ".env.keycloak-db.example", False),
)


def cmd_env_check(args: argparse.Namespace) -> int:
    directory = Path(args.dir)
    if not (directory / ".env").is_file():
        print(f"BEFUND: {directory / '.env'} fehlt")
        return EXIT_FINDING
    findings: list[str] = []
    checked: list[str] = []
    production = parse_env(directory / ".env").get("APP_ENV") == "production"
    for name, example_name, runtime in ENV_FILES:
        path = directory / name
        if not path.is_file():
            # db and migrate need .env.db in production (docker-compose.prod.yml); the
            # Keycloak files stay optional because an external identity provider works too.
            if production and name in _REQUIRED_IN_PRODUCTION:
                findings.append(f"{name} fehlt (Pflicht in Produktion)")
            continue
        checked.append(name)
        findings.extend(check_env_file(path, directory / example_name, runtime=runtime))
    print(f"Geprüft: {', '.join(checked)}")
    for finding in findings:
        print(f"BEFUND: {finding}")
    if not findings:
        print("Secrets: keine Befunde")
    return EXIT_FINDING if findings else EXIT_OK


# ---------------------------------------------------------------------- init-env

# (file, template, {key: generator name}) — generated only in files created now.
_INIT_FILES: tuple[tuple[str, str, dict[str, str]], ...] = (
    (
        ".env",
        ".env.example",
        {"SECRET_KEY": "hex", "APP_DB_PASSWORD": "url", "VALKEY_PASSWORD": "url"},
    ),
    (".env.db", ".env.db.example", {"POSTGRES_PASSWORD": "url"}),
    (
        ".env.keycloak",
        ".env.keycloak.example",
        {"KC_BOOTSTRAP_ADMIN_PASSWORD": "url", "KC_DB_PASSWORD": "keycloak-db"},
    ),
    (".env.keycloak-db", ".env.keycloak-db.example", {"POSTGRES_PASSWORD": "keycloak-db"}),
)


def _new_secret(kind: str) -> str:
    # URL-safe: VALKEY_PASSWORD and APP_DB_PASSWORD end up inside connection URLs.
    return secrets.token_hex(32) if kind == "hex" else secrets.token_urlsafe(32)


def set_env_value(lines: list[str], key: str, value: str) -> list[str]:
    """Set KEY in place: replace the active line, else uncomment `# KEY=`, else append."""
    active = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}=")
    commented = re.compile(rf"^\s*#\s*{re.escape(key)}=")
    out: list[str] = []
    done = False
    for line in lines:
        if active.match(line):
            if not done:
                out.append(f"{key}={value}")
                done = True
            continue  # drop later duplicates: the last definition would win
        out.append(line)
    if not done:
        for i, line in enumerate(out):
            if commented.match(line):
                out[i] = f"{key}={value}"
                done = True
                break
    if not done:
        out.append(f"{key}={value}")
    return out


def _replace_url_password(lines: list[str], key: str, password: str) -> list[str]:
    """Keep the host-execution URL (DATABASE_URL, VALKEY_URL) in step with the password."""
    pattern = re.compile(rf"^({re.escape(key)}=[^:/]+://[^:/@]*:)([^@]*)(@.*)$")
    return [pattern.sub(lambda m: m.group(1) + password + m.group(3), line) for line in lines]


def _write_private(path: Path, lines: list[str]) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def cmd_init_env(args: argparse.Namespace) -> int:
    directory = Path(args.dir)
    missing = [t for _, t, _ in _INIT_FILES if not (directory / t).is_file()]
    if missing:
        print(f"Vorlagen fehlen in {directory}: {', '.join(missing)}", file=sys.stderr)
        return EXIT_ENV
    settings = {
        "APP_ENV": "production",
        "COMPOSE_FILE": args.compose_file,
        "APP_VERSION": args.app_version,
        "APP_HOST": args.app_host,
        "AUTH_HOST": args.auth_host,
        "BACKUP_ENCRYPT_KEY": args.backup_key,
    }
    keycloak_db = None
    for name in (".env.keycloak", ".env.keycloak-db"):
        existing = directory / name
        if existing.is_file():
            values = parse_env(existing)
            keycloak_db = values.get(
                "KC_DB_PASSWORD" if name == ".env.keycloak" else "POSTGRES_PASSWORD"
            )
            if keycloak_db:
                break
    keycloak_db = keycloak_db or _new_secret("url")
    for name, template, generated in _INIT_FILES:
        path = directory / name
        if path.exists():
            print(f"{name}: vorhanden, bleibt unverändert")
            continue
        lines = (directory / template).read_text(encoding="utf-8").splitlines()
        keys: list[str] = []
        for key, kind in generated.items():
            value = keycloak_db if kind == "keycloak-db" else _new_secret(kind)
            lines = set_env_value(lines, key, value)
            if key == "APP_DB_PASSWORD":
                lines = _replace_url_password(lines, "DATABASE_URL", value)
            elif key == "VALKEY_PASSWORD":
                lines = _replace_url_password(lines, "VALKEY_URL", value)
            keys.append(key)
        if name == ".env":
            for key, value in settings.items():
                if value:
                    lines = set_env_value(lines, key, value)
                    keys.append(key)
        if args.dry_run:
            print(f"{name}: würde aus {template} angelegt (0600), gesetzt: {', '.join(keys)}")
            continue
        _write_private(path, lines)
        print(f"{name}: angelegt aus {template} (0600), gesetzt: {', '.join(keys)}")
    return EXIT_OK


# ------------------------------------------------------------------------- main


class _SafeParser(argparse.ArgumentParser):
    """Never echo argument values in errors: they could be secrets."""

    def error(self, message: str) -> None:
        self.exit(EXIT_USAGE, f"nakops: ungültige Argumente ({message.split(':')[0]})\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _SafeParser(prog="nakops.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_SafeParser)

    p = sub.add_parser("analyze-logs")
    p.add_argument("--json", action="store_true")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--fail-on-errors", action="store_true")
    p.set_defaults(func=cmd_analyze_logs)

    p = sub.add_parser("redact")
    p.set_defaults(func=cmd_redact)

    p = sub.add_parser("queue-histogram")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_queue_histogram)

    p = sub.add_parser("backups")
    p.add_argument("--dir", required=True)
    p.add_argument("--db", required=True)
    p.add_argument("--max-age-hours", type=float)
    p.add_argument("--latest-paths", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_backups)

    p = sub.add_parser("env-check")
    p.add_argument("--dir", required=True)
    p.set_defaults(func=cmd_env_check)

    p = sub.add_parser("init-env")
    p.add_argument("--dir", required=True)
    p.add_argument("--compose-file", default="docker-compose.prod.yml")
    p.add_argument("--app-version", default="")
    p.add_argument("--app-host", default="")
    p.add_argument("--auth-host", default="")
    p.add_argument("--backup-key", default="")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_init_env)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BrokenPipeError:
        # `nakctl ... | head` must not print a traceback.
        devnull = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(devnull, sys.stdout.fileno())
        finally:
            os.close(devnull)
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
