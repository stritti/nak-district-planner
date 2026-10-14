## 0. Erledigt vor dem Neuzuschnitt (2026-10-07)

- [x] 0.1 Connector-Registry `_CONNECTOR_MAP` in `sync_service.py` (Spec `calendar-connector`)
- [x] 0.2 Typisiertes `SyncResult` statt `dict[str, int]` (Spec `calendar-sync`)
- [x] 0.3 Einheitliche `Depends(get_<repository>)`-Injektion in allen Routern
- [x] 0.4 `GET /health` mit DB- und Valkey-Prüfung (Spec `production-deployment`)
- [x] 0.5 `MatrixFilters.vue` und `MatrixTable.vue` aus `MatrixView.vue` extrahiert

## 1. EventListView

- [ ] 1.1 `EventFilters.vue` extrahieren
- [ ] 1.2 `EventTable.vue` extrahieren
- [ ] 1.3 `EventFormModal.vue` extrahieren

## 2. CalendarIntegrationsView

- [ ] 2.1 `IntegrationCard.vue` extrahieren
- [ ] 2.2 `IntegrationFormModal.vue` extrahieren

## 3. LeadersAdminView und DistrictsAdminView

- [ ] 3.1 Leader-Liste und Leader-Formular aus `LeadersAdminView.vue` extrahieren (Abwesenheiten liegen bereits in `LeaderUnavailabilityForm.vue`/`LeaderUnavailabilityList.vue`)
- [ ] 3.2 Bezirks-, Gemeinde- und Gruppenformulare aus `DistrictsAdminView.vue` extrahieren

## 4. Verifikation

- [ ] 4.1 Frontend-Unit-Tests, ESLint und Playwright-E2E bestehen unverändert
