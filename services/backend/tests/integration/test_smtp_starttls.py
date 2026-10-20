# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Real-socket STARTTLS authentication and certificate regression tests (#627)."""

from __future__ import annotations

import runpy
import socketserver
import ssl
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app.adapters.mail import smtp as smtp_adapter
from app.adapters.mail.smtp import SmtpMailService
from app.domain.ports.mail import MailDeliveryError

PROBE = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "scripts" / "check_smtp_starttls.py")
)
verify_smtp_starttls = PROBE["verify_smtp_starttls"]
SmtpTlsProbeError = PROBE["SmtpTlsProbeError"]


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        context: ssl.SSLContext,
        *,
        offer_starttls: bool = True,
        break_tls: bool = False,
        fail_second_ehlo: bool = False,
        auth: str | None = "PLAIN LOGIN",
    ):
        self.tls_context = context
        self.offer_starttls = offer_starttls
        self.break_tls = break_tls
        self.fail_second_ehlo = fail_second_ehlo
        self.auth = auth
        self.events: list[tuple[str, bool]] = []
        super().__init__(("127.0.0.1", 0), _Handler)


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        tls = False
        self.wfile.write(b"220 localhost test server\r\n")
        self.wfile.flush()
        while line := self.rfile.readline():
            cmd = line.decode("ascii", errors="replace").strip().split(" ", 1)[0].upper()
            self.server.events.append((cmd, tls))
            if cmd == "EHLO":
                if tls and self.server.fail_second_ehlo:
                    self.wfile.write(b"554 EHLO denied after TLS\r\n")
                    self.wfile.flush()
                    continue
                advertised = b"250-localhost\r\n"
                if self.server.offer_starttls and not tls:
                    advertised += b"250-STARTTLS\r\n"
                if tls and self.server.auth is not None:
                    advertised += f"250-AUTH {self.server.auth}".rstrip().encode() + b"\r\n"
                self.wfile.write(advertised + b"250 HELP\r\n")
            elif cmd == "STARTTLS":
                if not self.server.offer_starttls:
                    self.wfile.write(b"454 TLS unavailable\r\n")
                else:
                    self.wfile.write(b"220 Ready to start TLS\r\n")
                    self.wfile.flush()
                    if self.server.break_tls:
                        return
                    try:
                        self.connection = self.server.tls_context.wrap_socket(
                            self.connection, server_side=True
                        )
                    except ssl.SSLError:
                        return
                    self.rfile = self.connection.makefile("rb")
                    self.wfile = self.connection.makefile("wb")
                    tls = True
            elif cmd == "AUTH":
                self.wfile.write(
                    b"235 2.7.0 Authentication successful\r\n" if tls else b"538 TLS required\r\n"
                )
            elif cmd in ("MAIL", "RCPT", "RSET"):
                self.wfile.write(b"250 OK\r\n")
            elif cmd == "DATA":
                self.wfile.write(b"354 End with <CRLF>.<CRLF>\r\n")
                self.wfile.flush()
                while item := self.rfile.readline():
                    if item == b".\r\n":
                        break
                self.server.events.append(("BODY", tls))
                self.wfile.write(b"250 Message accepted\r\n")
            elif cmd == "QUIT":
                self.wfile.write(b"221 Bye\r\n")
                self.wfile.flush()
                return
            else:
                self.wfile.write(b"500 Unsupported\r\n")
            self.wfile.flush()


@pytest.fixture
def certificate(tmp_path: Path) -> tuple[Path, Path]:
    cert, key = tmp_path / "test.crt", tmp_path / "test.key"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-days",
            "1",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
        ],
        capture_output=True,
        check=True,
        timeout=10,
    )
    return cert, key


@pytest.fixture
def tls_context(certificate: tuple[Path, Path]) -> ssl.SSLContext:
    cert, key = certificate
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(cert), str(key))
    return context


@pytest.fixture
def server_factory(tls_context: ssl.SSLContext) -> Iterator[Any]:
    servers: list[_Server] = []

    def start(
        *,
        offer_starttls: bool = True,
        break_tls: bool = False,
        fail_second_ehlo: bool = False,
        auth: str | None = "PLAIN LOGIN",
    ) -> _Server:
        server = _Server(
            tls_context,
            offer_starttls=offer_starttls,
            break_tls=break_tls,
            fail_second_ehlo=fail_second_ehlo,
            auth=auth,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


def _adapter(server: _Server, *, hostname: str = "localhost") -> SmtpMailService:
    return SmtpMailService(
        host=hostname,
        port=server.server_address[1],
        username="user",
        password="test-pass",
        from_address="sender@example.test",
        timeout=3,
    )


def _trust_test_cert(monkeypatch: pytest.MonkeyPatch, cert: Path) -> None:
    real_factory = ssl.create_default_context
    monkeypatch.setattr(
        smtp_adapter.ssl, "create_default_context", lambda: real_factory(cafile=str(cert))
    )


# Commands that carry credentials or mail content; none may cross an unverified channel.
_SENSITIVE = frozenset({"AUTH", "MAIL", "RCPT", "DATA", "BODY"})


def _assert_no_pre_tls_auth(events: list[tuple[str, bool]]) -> None:
    assert all(tls for command, tls in events if command in _SENSITIVE)


def _assert_nothing_sensitive_sent(events: list[tuple[str, bool]]) -> None:
    assert not any(command in _SENSITIVE for command, _ in events)


def test_trusted_starttls_authenticates_only_after_handshake(
    monkeypatch: pytest.MonkeyPatch, certificate: tuple[Path, Path], server_factory
) -> None:
    _trust_test_cert(monkeypatch, certificate[0])
    server = server_factory()
    _adapter(server).send(["receiver@example.test"], "Test", "Hello")
    assert ("STARTTLS", False) in server.events
    assert ("EHLO", True) in server.events
    assert ("AUTH", True) in server.events
    assert ("BODY", True) in server.events
    _assert_no_pre_tls_auth(server.events)
    commands = [cmd for cmd, _ in server.events]
    required = ["EHLO", "STARTTLS", "EHLO", "AUTH", "MAIL", "RCPT", "DATA", "BODY"]
    assert commands[: len(required)] == required


def test_missing_starttls_never_sends_credentials(server_factory) -> None:
    server = server_factory(offer_starttls=False)
    with pytest.raises(MailDeliveryError):
        _adapter(server).send(["receiver@example.test"], "Test", "Hello")
    _assert_nothing_sensitive_sent(server.events)


def test_untrusted_certificate_never_authenticates(server_factory) -> None:
    server = server_factory()
    with pytest.raises(MailDeliveryError):
        _adapter(server).send(["receiver@example.test"], "Test", "Hello")
    _assert_nothing_sensitive_sent(server.events)


def test_hostname_mismatch_never_authenticates(
    monkeypatch: pytest.MonkeyPatch, certificate: tuple[Path, Path], server_factory
) -> None:
    _trust_test_cert(monkeypatch, certificate[0])
    server = server_factory()
    with pytest.raises(MailDeliveryError):
        _adapter(server, hostname="127.0.0.1").send(["receiver@example.test"], "Test", "Hello")
    _assert_nothing_sensitive_sent(server.events)


def test_failed_tls_upgrade_never_authenticates(
    monkeypatch: pytest.MonkeyPatch, certificate: tuple[Path, Path], server_factory
) -> None:
    _trust_test_cert(monkeypatch, certificate[0])
    server = server_factory(break_tls=True)
    with pytest.raises(MailDeliveryError):
        _adapter(server).send(["receiver@example.test"], "Test", "Hello")
    _assert_nothing_sensitive_sent(server.events)


def test_relay_preflight_verifies_tls_without_authentication(
    certificate: tuple[Path, Path], server_factory
) -> None:
    cert, _ = certificate
    server = server_factory()
    verify_smtp_starttls(
        host="localhost",
        port=server.server_address[1],
        context=ssl.create_default_context(cafile=str(cert)),
    )
    assert ("STARTTLS", False) in server.events
    assert ("EHLO", True) in server.events
    _assert_nothing_sensitive_sent(server.events)


def test_relay_preflight_fails_when_starttls_unavailable(server_factory) -> None:
    server = server_factory(offer_starttls=False)
    with pytest.raises(SmtpTlsProbeError):
        verify_smtp_starttls(host="localhost", port=server.server_address[1])
    _assert_nothing_sensitive_sent(server.events)


def test_relay_preflight_rejects_failed_ehlo_after_tls(
    certificate: tuple[Path, Path], server_factory
) -> None:
    server = server_factory(fail_second_ehlo=True)
    with pytest.raises(SmtpTlsProbeError, match="EHLO"):
        verify_smtp_starttls(
            host="localhost",
            port=server.server_address[1],
            context=ssl.create_default_context(cafile=str(certificate[0])),
        )
    _assert_nothing_sensitive_sent(server.events)


@pytest.mark.parametrize("auth", [None, "", "XOAUTH2"], ids=["absent", "empty", "unsupported"])
def test_relay_preflight_rejects_unusable_post_tls_auth(
    certificate: tuple[Path, Path], server_factory, auth: str | None
) -> None:
    server = server_factory(auth=auth)
    with pytest.raises(SmtpTlsProbeError, match="AUTH"):
        verify_smtp_starttls(
            host="localhost",
            port=server.server_address[1],
            context=ssl.create_default_context(cafile=str(certificate[0])),
        )
    assert ("EHLO", True) in server.events
    _assert_nothing_sensitive_sent(server.events)


def test_relay_preflight_names_a_rejected_certificate(server_factory) -> None:
    server = server_factory()
    with pytest.raises(SmtpTlsProbeError, match="certificate rejected"):
        verify_smtp_starttls(host="localhost", port=server.server_address[1])
    _assert_nothing_sensitive_sent(server.events)


def test_unauthenticated_internal_relay_delivers_without_starttls(server_factory) -> None:
    """The supported no-auth relay mode (no credentials, STARTTLS off) still delivers."""
    server = server_factory(offer_starttls=False)
    SmtpMailService(
        host="localhost",
        port=server.server_address[1],
        username=None,
        password=None,
        from_address="sender@example.test",
        use_starttls=False,
        timeout=3,
    ).send(["receiver@example.test"], "Test", "Hello")
    commands = [command for command, _ in server.events]
    assert "BODY" in commands
    assert "STARTTLS" not in commands and "AUTH" not in commands
