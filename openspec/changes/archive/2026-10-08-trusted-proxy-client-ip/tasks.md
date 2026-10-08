## 1. Backend

- [x] 1.1 Gemeinsame `get_client_ip()` mit `TRUSTED_PROXIES`-Pruefung implementieren (Tests zuerst).
- [x] 1.2 Rate-Limit- und Audit-Middleware auf `get_client_ip()` umstellen.
- [x] 1.3 Ungueltige `TRUSTED_PROXIES` beim Start ablehnen.
- [x] 1.4 uvicorn mit `--no-proxy-headers` starten (Dockerfile, Dev-Override).

## 2. frontend-nginx

- [x] 2.1 `set_real_ip_from` aus `NGINX_REAL_IP_FROM` generieren; `real_ip_header X-Forwarded-For; real_ip_recursive on;`.
- [x] 2.2 Bereinigtes `X-Forwarded-For` und `X-Forwarded-Proto` (Fallback `$scheme`) an das Backend senden.
- [x] 2.3 `NGINX_REAL_IP_FROM` per `.env.docker.frontend` (aus `.env` interpoliert) statt `environment:`; das Frontend laedt `.env` nicht.

## 3. Dokumentation

- [x] 3.1 Runbook-Abschnitt zu Reverse Proxy und Client-IP.
- [x] 3.2 `TRUSTED_PROXIES` und `NGINX_REAL_IP_FROM` in `.env.example`.
