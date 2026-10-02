## 1. Contract baseline
- [ ] Specify provider-neutral fetch/delete/update capabilities and typed errors.
- [ ] Add reusable connector contract tests.
- [ ] Capture PR #375 pagination/retry behavior as characterization tests.

## 2. SDK evaluation
- [ ] Evaluate Google API Python client and viable maintained alternatives.
- [ ] Evaluate Microsoft Graph SDK and viable maintained alternatives.
- [ ] Document keep-httpx vs SDK decision independently per provider.

## 3. Adapter implementation
- [ ] Implement the selected Google adapter behind CalendarConnector.
- [ ] Implement the selected Microsoft adapter behind CalendarConnector.
- [ ] Implement token refresh persistence without exposing secrets.
- [ ] Normalize pagination, Retry-After/throttling, timeout, and errors.

## 4. Verification
- [ ] Run shared contract tests for both providers.
- [ ] Test multi-page, 429, 5xx, timeout, expired token, malformed response, and cancellation cases.
- [ ] Verify no SDK/provider types leak into domain/application modules.
- [ ] Run backend tests, lint/security checks, and coverage >= 80%.
