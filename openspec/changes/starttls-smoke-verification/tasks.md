## 1. Local protocol test harness
- [ ] 1.1 Pin local SMTP test server dev dependency and ephemeral certificate fixture.
- [ ] 1.2 Write failing real-socket tests for valid STARTTLS and authentication ordering.
- [ ] 1.3 Add missing STARTTLS, untrusted certificate, hostname mismatch and handshake-failure cases.

## 2. Production verification
- [ ] 2.1 Implement or document non-delivering staging STARTTLS handshake smoke command.
- [ ] 2.2 Update production runbook with actual relay verification gate and evidence format.

## 3. CI
- [ ] 3.1 Run integration suite in CI without real network/credentials.
- [ ] 3.2 Run full checks and backend coverage >=80%; independent review.
