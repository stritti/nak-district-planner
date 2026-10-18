# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Credential-free verification of a relay's STARTTLS handshake."""

from __future__ import annotations

import argparse
import smtplib
import ssl

from app.domain.ports.mail import MailDeliveryError


def verify_smtp_starttls(
    *, host: str, port: int, timeout: float = 10.0, context: ssl.SSLContext | None = None
) -> None:
    """Check STARTTLS and certificate/hostname without AUTH or sending mail."""
    try:
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            smtp.ehlo()
            if not smtp.has_extn("starttls"):
                raise MailDeliveryError("SMTP relay does not offer STARTTLS")
            smtp.starttls(context=context or ssl.create_default_context())
            smtp.ehlo()
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        raise MailDeliveryError("SMTP relay TLS handshake not verified") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify SMTP STARTTLS; never sends AUTH or email")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    try:
        verify_smtp_starttls(host=args.host, port=args.port)
    except MailDeliveryError:
        print("FAIL: SMTP relay STARTTLS or certificate verification failed")
        return 1
    print("PASS: SMTP relay STARTTLS and hostname verification completed (no AUTH sent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
