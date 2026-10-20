## 1. Local protocol test harness
- [x] 1.1 Local SMTP test server (stdlib `socketserver`, no extra dependency) and ephemeral certificate fixture.
- [x] 1.2 Write failing real-socket tests for valid STARTTLS and authentication ordering.
- [x] 1.3 Add missing STARTTLS, untrusted certificate, hostname mismatch and handshake-failure cases.

## 2. Production verification
- [x] 2.1 Implement or document non-delivering staging STARTTLS handshake smoke command.
- [x] 2.2 Update production runbook with actual relay verification gate and evidence format.

## 3. CI
- [x] 3.1 Run integration suite in CI without real network/credentials.
- [x] 3.2 Run full checks and backend coverage >=80%; independent review.
