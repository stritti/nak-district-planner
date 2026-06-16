# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: events-crud.spec.ts >> Event list CRUD >> renders event list with mocked data
- Location: tests/e2e/events-crud.spec.ts:26:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('Gottesdienst')
Expected: visible
Error: strict mode violation: getByText('Gottesdienst') resolved to 2 elements:
    1) <td class="table-td font-medium text-gray-900 dark:text-gray-100">Gottesdienst</td> aka getByRole('cell', { name: 'Gottesdienst' }).first()
    2) <td class="table-td">Gottesdienst</td> aka getByRole('cell', { name: 'Gottesdienst' }).nth(1)

Call log:
  - Expect "toBeVisible" with timeout 10000ms
  - waiting for getByText('Gottesdienst')

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - navigation [ref=e4]:
    - generic [ref=e6]:
      - generic [ref=e7]:
        - generic [ref=e8]: NAK Bezirksplaner
        - generic [ref=e9]:
          - link "Ereignisse" [ref=e10] [cursor=pointer]:
            - /url: /events
            - img [ref=e11]
            - text: Ereignisse
          - link "Dienstplan-Matrix" [ref=e13] [cursor=pointer]:
            - /url: /matrix
            - img [ref=e14]
            - text: Dienstplan-Matrix
          - link "Bezirke & Gemeinden" [ref=e16] [cursor=pointer]:
            - /url: /admin/districts
            - img [ref=e17]
            - text: Bezirke & Gemeinden
          - link "Amtstragende" [ref=e19] [cursor=pointer]:
            - /url: /admin/leaders
            - img [ref=e20]
            - text: Amtstragende
          - link "Kalender" [ref=e22] [cursor=pointer]:
            - /url: /admin/calendars
            - img [ref=e23]
            - text: Kalender
          - link "Export" [ref=e25] [cursor=pointer]:
            - /url: /admin/export
            - img [ref=e26]
            - text: Export
      - generic [ref=e28]:
        - button "Dark Mode aktivieren" [ref=e29]:
          - img [ref=e30]
        - button "Planner planner@example.com" [ref=e33]:
          - generic [ref=e34]:
            - generic [ref=e35]: Planner
            - generic [ref=e36]: planner@example.com
          - img [ref=e37]
  - generic [ref=e40]: "Freigabe ausstehend: Ihr Konto ist angemeldet, aber noch keinem Bezirk oder keiner Gemeinde zugeordnet."
  - main [ref=e41]:
    - generic [ref=e42]:
      - generic [ref=e43]:
        - generic [ref=e44]:
          - heading "Ereignisse" [level=1] [ref=e45]
          - generic [ref=e46]: 1 gesamt
        - generic [ref=e47]:
          - button "Excel (max. 10.000)" [ref=e49]:
            - img [ref=e50]
            - text: Excel (max. 10.000)
          - generic [ref=e52]:
            - button "Liste" [ref=e53]
            - button "Woche" [ref=e54]
            - button "Monat" [ref=e55]
      - generic [ref=e56]:
        - generic [ref=e58]:
          - generic [ref=e59]: "Schnellfilter:"
          - generic [ref=e60]:
            - button "Aktueller Monat" [ref=e61]
            - button "Kommender Monat" [ref=e62]
            - button "Alle" [ref=e63]
        - generic [ref=e64]:
          - generic [ref=e65]:
            - generic [ref=e66]: Bezirk
            - combobox [ref=e67]:
              - option "Bezirk Test" [selected]
          - generic [ref=e68]:
            - generic [ref=e69]: Gemeinde
            - combobox [ref=e70]:
              - option "Alle Gemeinden" [selected]
              - option "Nur Bezirksebene"
          - generic [ref=e71]:
            - generic [ref=e72]: Status
            - combobox [ref=e73]:
              - option "Alle" [selected]
              - option "Entwurf"
              - option "Veröffentlicht"
              - option "Abgesagt"
          - generic [ref=e74]:
            - generic [ref=e75]: Freigabe
            - combobox [ref=e76]:
              - option "Alle" [selected]
              - option "Geplant"
              - option "Bestätigt"
          - generic [ref=e77]:
            - generic [ref=e78]: Von
            - textbox [ref=e79]
          - generic [ref=e80]:
            - generic [ref=e81]: Bis
            - textbox [ref=e82]
      - table [ref=e85]:
        - rowgroup [ref=e86]:
          - row "Titel Start Kategorie Zuordnung Einladung Status Freigabe Quelle" [ref=e87]:
            - columnheader "Titel" [ref=e88]
            - columnheader "Start" [ref=e89]
            - columnheader "Kategorie" [ref=e90]
            - columnheader "Zuordnung" [ref=e91]
            - columnheader "Einladung" [ref=e92]
            - columnheader "Status" [ref=e93]
            - columnheader "Freigabe" [ref=e94]
            - columnheader "Quelle" [ref=e95]
            - columnheader [ref=e96]
        - rowgroup [ref=e97]:
          - row "Gottesdienst 01.06.2026, 10:00 Gottesdienst Bezirk Test(Bezirk) — Veröffentlicht ✓ Bestätigt Intern" [ref=e98]:
            - cell "Gottesdienst" [ref=e99]
            - cell "01.06.2026, 10:00" [ref=e100]
            - cell "Gottesdienst" [ref=e101]
            - cell "Bezirk Test(Bezirk)" [ref=e102]
            - cell "—" [ref=e103]
            - cell "Veröffentlicht" [ref=e104]
            - cell "✓ Bestätigt" [ref=e105]:
              - generic [ref=e106]:
                - generic [ref=e107]: ✓
                - text: Bestätigt
            - cell "Intern" [ref=e108]
            - cell [ref=e109]:
              - button "Zuordnung bearbeiten" [ref=e110]:
                - img [ref=e111]
```

# Test source

```ts
  1  | import { expect, test } from '@playwright/test'
  2  | 
  3  | const FRONTEND_URL = 'http://localhost:5173'
  4  | 
  5  | const AUTH = {
  6  |   token: {
  7  |     accessToken: 'fake-access-token',
  8  |     idToken: 'fake-id-token',
  9  |     expiresAt: Math.floor(Date.now() / 1000) + 3600,
  10 |   },
  11 |   user: { sub: 'planner-1', email: 'planner@example.com', name: 'Planner' },
  12 |   isSuperadmin: false,
  13 |   accessStatus: 'ACTIVE' as const,
  14 |   memberships: [
  15 |     { role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' },
  16 |   ],
  17 | }
  18 | 
  19 | test.describe('Event list CRUD', () => {
  20 |   test.beforeEach(async ({ page }) => {
  21 |     await page.addInitScript((auth) => {
  22 |       localStorage.setItem('auth', JSON.stringify(auth))
  23 |     }, AUTH)
  24 |   })
  25 | 
  26 |   test('renders event list with mocked data', async ({ page }) => {
  27 |     // Catch-all registered FIRST → lowest priority (runs last in Playwright's reverse order)
  28 |     await page.route('**/api/v1/**', async (route) => {
  29 |       await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  30 |     })
  31 |     await page.route('**/api/v1/events**', async (route) => {
  32 |       await route.fulfill({
  33 |         status: 200,
  34 |         contentType: 'application/json',
  35 |         body: JSON.stringify({
  36 |           items: [
  37 |             {
  38 |               id: 'ev-1',
  39 |               title: 'Gottesdienst',
  40 |               start_at: '2026-06-01T10:00:00Z',
  41 |               end_at: '2026-06-01T12:00:00Z',
  42 |               district_id: 'district-1',
  43 |               category: 'Gottesdienst',
  44 |               status: 'PUBLISHED',
  45 |               source: 'INTERNAL',
  46 |               visibility: 'INTERNAL',
  47 |             },
  48 |           ],
  49 |           total: 1,
  50 |           limit: 50,
  51 |           offset: 0,
  52 |         }),
  53 |       })
  54 |     })
  55 |     await page.route('**/api/v1/districts', async (route) => {
  56 |       await route.fulfill({
  57 |         status: 200,
  58 |         contentType: 'application/json',
  59 |         body: JSON.stringify([{ id: 'district-1', name: 'Bezirk Test' }]),
  60 |       })
  61 |     })
  62 | 
  63 |     await page.goto(`${FRONTEND_URL}/events`)
> 64 |     await expect(page.getByText('Gottesdienst')).toBeVisible({ timeout: 10000 })
     |                                                  ^ Error: expect(locator).toBeVisible() failed
  65 |   })
  66 | })
  67 | 
```