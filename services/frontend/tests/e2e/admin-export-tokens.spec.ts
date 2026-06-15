import { expect, test } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

const ADMIN_AUTH = {
  token: { accessToken: 'admin-token', idToken: 'admin-id-token', expiresAt: Math.floor(Date.now() / 1000) + 3600 },
  user: { sub: 'admin-1', email: 'admin@example.com', name: 'Admin' },
  isSuperadmin: true,
  accessStatus: 'ACTIVE' as const,
  memberships: [{ role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'district-1' }],
}

test.describe('Export tokens view', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((auth) => {
      localStorage.setItem('auth', JSON.stringify(auth))
    }, JSON.stringify(ADMIN_AUTH))
  })

  test('renders export tokens page', async ({ page }) => {
    await page.route('**/api/v1/export-tokens', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'tok-1', label: 'Public Feed', token: 'pub_abc123', token_type: 'PUBLIC', district_id: 'district-1' },
        ]),
      })
    })
    await page.route('**/api/v1/districts', async (route) => {
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify([{ id: 'district-1', name: 'Bezirk München' }]),
      })
    })

    await page.goto(`${FRONTEND_URL}/admin/export`)
    await expect(page.getByRole('heading', { name: /Export/i })).toBeVisible({ timeout: 10000 })
  })
})
