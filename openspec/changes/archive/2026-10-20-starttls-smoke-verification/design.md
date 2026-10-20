# Real STARTTLS Verification

## Current adapter

`app/adapters/mail/smtp.py` wraps `smtplib.SMTP`, performs `ehlo`, then `starttls(context=ssl.create_default_context())`, `ehlo` and finally `login`. It raises `MailDeliveryError` for protocol/network failures. Existing tests use mocks instead of TLS handshakes.

## Local integration harness

Start a real loopback SMTP test server bound to an ephemeral port, managed by a pytest fixture and cleaned up after every case. Prefer `aiosmtpd` for the protocol engine and a temporary self-signed server certificate whose SAN matches the host used in the client connection, or an equivalently controlled local server. Generate ephemeral certificate material in a private temporary directory; never commit keys. The positive test explicitly trusts only the test CA via monkeypatched context factory, *without disabling hostname verification*.

Capture protocol events on the local server. Verify `EHLO -> STARTTLS -> handshake -> EHLO -> AUTH -> MAIL/RCPT/DATA` in order, and verify address isolation remains intact. Add a server with no STARTTLS capability: authentication must not occur and send must fail. Test an untrusted certificate and hostname mismatch: no AUTH and no message accepted. Test a server that advertises STARTTLS but fails the upgrade: no authentication. Verify the no-auth relay path separately, preserving the existing configurable behavior.

Keep credentials out of test snapshots, failure logs and exception messages. The harness runs in CI without external network or DNS.

## Staging smoke procedure

A command that executes a single non-destructive SMTP handshake against the configured relay verifies advertised STARTTLS, certificate chain, SAN hostname, TLS protocol version and whether authentication is *eligible* after the handshake. Use a deliberately non-delivering diagnostic mode; it must not log credentials and must not attempt real delivery during a preflight. A second staging test with designated test credentials/test mailbox may verify real authenticated delivery under operator control. Document execution and results in `docs/operations/production-runbook.md`; production test is a manual rollout gate, not a CI assertion.

## CI and acceptance

Add the new tests to `services/backend/tests/integration` with any needed dev-only dependency pinned in `uv.lock`. CI shall run all success and failure cases and retain coverage >=80%. Production relay verification must be recorded by the operator; local tests cannot certify the operator's actual TLS proxy/relay.
