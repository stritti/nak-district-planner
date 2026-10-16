### Geheime ICS-Feed-URLs in Zugriffslogs

**Betroffen:**

Alle Installationen mit Kalenderabonnements. Der Token steht im URL-Pfad (`/api/v1/export/<token>/calendar.ics`). Anwendung und mitgeliefertes Frontend-nginx maskieren ihn jetzt in Logs. Ein vorgeschalteter externer TLS-Proxy oder Load Balancer ist nicht Teil des Repos und kann den Token weiterhin protokollieren. Zusätzlich enthalten bereits geschriebene Logs möglicherweise gültige Feed-URLs.

**Vor dem Update:**

- Konfiguration des externen Proxys prüfen und den Pfad `/api/v1/export/` maskieren oder nicht protokollieren.
- Das Frontend-Image neu bereitstellen, damit die neue nginx-Konfiguration (maskiertes `access_log`) aktiv wird.

**Nach dem Update:**

- Einen Feed abrufen und prüfen, dass weder Frontend-nginx-, Backend- noch Proxy-Logs den Token im Klartext enthalten.
- Aufbewahrungsfristen alter Logs prüfen. Token, die in Logs mit weitem Lesezugriff stehen, widerrufen und neu ausstellen.
