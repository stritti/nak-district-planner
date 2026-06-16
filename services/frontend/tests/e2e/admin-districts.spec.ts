import { expect, test } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

const ADMIN_AUTH = {
  token: {
    accessToken: 'admin-token',
    idToken: 'admin-id-token',
    expiresAt: Math.floor(Date.now() / 1000) + 3600,
  },
  user: { sub: 'admin-1', email: 'admin@example.com', name: 'Bezirksvorsteher' },
  isSuperadmin: true,
  accessStatus: 'ACTIVE' as const,
  memberships: [
    { role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'district-1' },
  ],
}

test.describe('Districts admin view', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((auth) => {
      localStorage.setItem('auth', JSON.stringify(auth))
    }, ADMIN_AUTH)
  })

  test('renders districts list', async ({ page }) => {
    await page.route('**/api/v1/districts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'd1', name: 'Bezirk München', state_code: 'BY' },
          { id: 'd2', name: 'Bezirk Stuttgart', state_code: 'BW' },
        ]),
      })
    })
    await page.route('**/api/v1/districts/*/congregations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ id: 'c1', name: 'Gemeinde A', district_id: 'd1' }]),
      })
    })
    await page.route('**/api/v1/districts/*/groups', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })

    await page.goto(`${FRONTEND_URL}/admin/districts`)
    await expect(page.getByRole('heading', { name: /Bezirk/i })).toBeVisible({ timeout: 10000 })
  })
})
