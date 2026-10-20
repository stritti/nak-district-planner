# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Credential-free SMTP STARTTLS preflight, independent of application settings.

Run: python3 scripts/check_smtp_starttls.py --host smtp.example.org --port 587
Only checks SMTP capabilities and TLS; sends no AUTH, MAIL, RCPT, or DATA.
"""

from __future__ import annotations

import argparse
import smtplib
import ssl


class SmtpTlsProbeError(RuntimeError):
    """The relay did not prove it is eligible for authenticated TLS delivery."""


# Mechanisms ``smtplib.SMTP.login()`` (used by the mail adapter) can negotiate.
_LOGIN_MECHANISMS = frozenset({"PLAIN", "LOGIN", "CRAM-MD5"})


def _failure_reason(exc: BaseException) -> str:
    """Credential-free failure category, e.g. a certificate or hostname problem."""
    if isinstance(exc, ssl.SSLCertVerificationError):
        return f"certificate rejected ({exc.verify_message})"
    if isinstance(exc, ssl.SSLError):
        return "TLS handshake failed"
    if isinstance(exc, TimeoutError):
        return "connection timed out"
    if isinstance(exc, OSError):
        return "connection failed"
    return "SMTP protocol error"


def verify_smtp_starttls(
    *, host: str, port: int, timeout: float = 10.0, context: ssl.SSLContext | None = None
) -> None:
    """Verify both SMTP EHLO replies, STARTTLS peer certificate and AUTH capability."""
    try:
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            code, _ = smtp.ehlo()
            if code != 250:
                raise SmtpTlsProbeError("SMTP pre-TLS EHLO failed")
            if not smtp.has_extn("starttls"):
                raise SmtpTlsProbeError("SMTP relay does not offer STARTTLS")

            smtp.starttls(context=context or ssl.create_default_context())
            code, _ = smtp.ehlo()
            if code != 250:
                raise SmtpTlsProbeError("SMTP post-TLS EHLO failed")
            # Case-sensitive, as smtplib.SMTP.login() matches the advertised tokens.
            offered = set((smtp.esmtp_features.get("auth") or "").split())
            if not offered & _LOGIN_MECHANISMS:
                raise SmtpTlsProbeError(
                    "SMTP relay offers no AUTH mechanism the adapter supports after STARTTLS"
                )
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        raise SmtpTlsProbeError(
            f"SMTP relay TLS handshake could not be verified: {_failure_reason(exc)}"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check SMTP STARTTLS and AUTH capability without authentication"
    )
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    try:
        verify_smtp_starttls(host=args.host, port=args.port)
    except SmtpTlsProbeError as exc:
        # Messages name the failing step only; no credentials are ever involved.
        print(f"FAIL: {exc}")
        return 1
    print("PASS: STARTTLS certificate, EHLO, and AUTH capability verified; no AUTH was sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
