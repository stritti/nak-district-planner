### SMTP-Anmeldung nur noch mit STARTTLS

**Betroffen:**

Produktivinstallationen, die `SMTP_USER` und `SMTP_PASSWORD` zusammen mit `SMTP_STARTTLS=false` konfiguriert haben. Der Produktionsstart (API, Worker, Beat) wird für diese Kombination abgelehnt, weil Zugangsdaten und Nachrichten sonst unverschlüsselt übertragen würden. Installationen mit `SMTP_STARTTLS=true` (Standard) oder ohne SMTP-Anmeldung sind nicht betroffen.

**Vor dem Update:**

- Die Werte `SMTP_USER`, `SMTP_PASSWORD` und `SMTP_STARTTLS` in der Produktionskonfiguration prüfen.
- Bei Anmeldung `SMTP_STARTTLS=true` setzen und sicherstellen, dass der Mailserver STARTTLS mit einem gültigen, zum Hostnamen passenden Zertifikat anbietet.
- Ein Relay ohne Anmeldung darf weiterhin ohne STARTTLS laufen (`SMTP_USER` und `SMTP_PASSWORD` leer lassen), nur in einem vertrauenswürdigen internen Netz.

**Nach dem Update:**

- Prüfen, dass API, Worker und Beat starten und eine Test-Mail (zum Beispiel eine Erinnerung) zugestellt wird.
- Schlägt die Zustellung mit „SMTP delivery failed“ fehl, STARTTLS-Unterstützung und Zertifikat des Mailservers prüfen. Das Passwort wird in diesem Fall nicht gesendet.
