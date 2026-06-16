# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: admin-districts.spec.ts >> Districts admin view >> renders districts list
- Location: tests/e2e/admin-districts.spec.ts:26:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: /Bezirk/i })
Expected: visible
Timeout: 10000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 10000ms
  - waiting for getByRole('heading', { name: /Bezirk/i })

```

```yaml
- navigation:
  - text: NAK Bezirksplaner
  - link "Ereignisse":
    - /url: /events
  - link "Dienstplan-Matrix":
    - /url: /matrix
  - link "Bezirke & Gemeinden":
    - /url: /admin/districts
  - link "Amtstragende":
    - /url: /admin/leaders
  - link "Kalender":
    - /url: /admin/calendars
  - link "Export":
    - /url: /admin/export
  - button "Dark Mode aktivieren"
  - button "Bezirksvorsteher admin@example.com":
    - text: Bezirksvorsteher admin@example.com
    - img
- text: "Freigabe ausstehend: Ihr Konto ist angemeldet, aber noch keinem Bezirk oder keiner Gemeinde zugeordnet."
- main
```

# Test source

```ts
  1  | import { expect, test } from '@playwright/test'
  2  | 
  3  | const FRONTEND_URL = 'http://localhost:5173'
  4  | 
  5  | const ADMIN_AUTH = {
  6  |   token: {
  7  |     accessToken: 'admin-token',
  8  |     idToken: 'admin-id-token',
  9  |     expiresAt: Math.floor(Date.now() / 1000) + 3600,
  10 |   },
  11 |   user: { sub: 'admin-1', email: 'admin@example.com', name: 'Bezirksvorsteher' },
  12 |   isSuperadmin: true,
  13 |   accessStatus: 'ACTIVE' as const,
  14 |   memberships: [
  15 |     { role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'district-1' },
  16 |   ],
  17 | }
  18 | 
  19 | test.describe('Districts admin view', () => {
  20 |   test.beforeEach(async ({ page }) => {
  21 |     await page.addInitScript((auth) => {
  22 |       localStorage.setItem('auth', JSON.stringify(auth))
  23 |     }, ADMIN_AUTH)
  24 |   })
  25 | 
  26 |   test('renders districts list', async ({ page }) => {
  27 |     await page.route('**/api/v1/districts', async (route) => {
  28 |       await route.fulfill({
  29 |         status: 200,
  30 |         contentType: 'application/json',
  31 |         body: JSON.stringify([
  32 |           { id: 'd1', name: 'Bezirk München', state_code: 'BY' },
  33 |           { id: 'd2', name: 'Bezirk Stuttgart', state_code: 'BW' },
  34 |         ]),
  35 |       })
  36 |     })
  37 |     await page.route('**/api/v1/districts/*/congregations', async (route) => {
  38 |       await route.fulfill({
  39 |         status: 200,
  40 |         contentType: 'application/json',
  41 |         body: JSON.stringify([{ id: 'c1', name: 'Gemeinde A', district_id: 'd1' }]),
  42 |       })
  43 |     })
  44 |     await page.route('**/api/v1/districts/*/groups', async (route) => {
  45 |       await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  46 |     })
  47 | 
  48 |     await page.goto(`${FRONTEND_URL}/admin/districts`)
> 49 |     await expect(page.getByRole('heading', { name: /Bezirk/i })).toBeVisible({ timeout: 10000 })
     |                                                                  ^ Error: expect(locator).toBeVisible() failed
  50 |   })
  51 | })
  52 | 
```