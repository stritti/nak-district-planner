# request-identity Specification

## Purpose
Legt fest, aus welchen Quellen Rate-Limiting und Audit-Log die Client-IP ableiten: nur von vertrauenswuerdigen Proxies, mit bereinigten Forwarding-Headern.

## Requirements

### Requirement: Client IP is derived only from trusted proxies
The backend SHALL determine the client IP for rate limiting and audit logging through a single shared function. It SHALL use the `X-Real-IP` header only when the TCP peer address lies in the configured `TRUSTED_PROXIES` networks and SHALL otherwise use the peer address. `X-Forwarded-For` SHALL NOT be used to determine the client IP.

#### Scenario: Two clients behind the trusted nginx
- **WHEN** two clients with different IPs send requests through the frontend nginx
- **THEN** the backend resolves each client's own IP from `X-Real-IP`
- **AND** each client is rate limited in a separate bucket

#### Scenario: Spoofed headers from an untrusted peer
- **WHEN** a peer outside `TRUSTED_PROXIES` sends `X-Real-IP` or `X-Forwarded-For`
- **THEN** the headers are ignored and the peer address is used

#### Scenario: Audit log uses the same client IP
- **WHEN** an audited request carries a client-supplied `X-Forwarded-For`
- **THEN** the audit entry records the IP returned by the shared function, not the header value

### Requirement: Frontend nginx restores and sanitizes the client IP
The frontend nginx SHALL accept the client IP from `X-Forwarded-For` only from peers listed in `NGINX_REAL_IP_FROM` and SHALL forward to the backend only `X-Real-IP` and `X-Forwarded-For` set to the resolved client IP, plus `X-Forwarded-Proto` from the upstream proxy or its own scheme.

#### Scenario: Request via the external TLS proxy
- **WHEN** the external proxy on a trusted address forwards a request with `X-Forwarded-For: <spoofed>, <client>`
- **THEN** nginx sends `X-Real-IP: <client>` and `X-Forwarded-For: <client>` to the backend

#### Scenario: Direct request from an untrusted address
- **WHEN** a peer outside `NGINX_REAL_IP_FROM` sends `X-Forwarded-For`
- **THEN** nginx forwards the peer address as client IP
