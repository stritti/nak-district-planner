# Runbook: Membership-Backfill vor Guard-Rollout

Ziel: Vor dem produktiven Erzwingen des Membership-Gates sicherstellen, dass bestehende Benutzer mindestens eine gueltige Membership haben.

## Wann anwenden

- Vor Deployment einer Version mit aktiviertem Access-Guard.
- Nach groesseren Migrationen von Rollen-/Scope-Daten.

## Vorgehen

1. Kandidaten ohne Membership identifizieren.
2. Fuer jeden Kandidaten den fachlich korrekten Scope bestimmen (Bezirk oder Gemeinde).
3. Memberships idempotent upserten (`user_sub`, `scope_type`, `scope_id`).
4. Stichprobe mit echten API-Aufrufen pruefen.

## SQL-Checks

Benutzer ohne Membership finden:

```sql
SELECT u.sub, u.email
FROM users u
LEFT JOIN memberships m ON m.user_sub = u.sub
WHERE m.id IS NULL
ORDER BY u.created_at;
```

Duplikat-Scopes je Benutzer pruefen:

```sql
SELECT user_sub, scope_type, scope_id, COUNT(*)
FROM memberships
GROUP BY user_sub, scope_type, scope_id
HAVING COUNT(*) > 1;
```

## Rollback

- Falls benoetigt, neuen Guard kurzfristig deaktivieren.
- Backfill-Eintraege koennen gezielt nach `user_sub/scope` korrigiert werden.

## Verifikation

- `GET /api/v1/auth/access` liefert fuer betroffene Benutzer `ACTIVE` und Membership-Liste.
- Geschuetzte Endpunkte antworten nicht mehr mit `403 Freigabe ausstehend`.
