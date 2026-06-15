import { expect, test } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

const ADMIN_AUTH = {
  token: {
    accessToken: 'admin-token',
    idToken: 'admin-id-token',
    expiresAt: Math.floor(Date.now() / 1000) + 3600,
  },
  user: { sub: 'admin-1', email: 'admin@example.com', name: 'Admin' },
  isSuperadmin: true,
  accessStatus: 'ACTIVE' as const,
  memberships: [
    { role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'district-1' },
  ],
}

test.describe('Leaders admin view', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((auth) => {
      localStorage.setItem('auth', JSON.stringify(auth))
    }, JSON.stringify(ADMIN_AUTH))
  })

  test('renders leaders list and allows adding', async ({ page }) => {
    await page.route('**/api/v1/districts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ id: 'district-1', name: 'Bezirk München' }]),
      })
    })
    await page.route('**/api/v1/districts/*/leaders', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'leader-1',
            name: 'Pastor Schmidt',
            rank: 'Ap.',
            is_active: true,
            congregation_id: null,
            district_id: 'district-1',
          },
        ]),
      })
    })

    await page.goto(`${FRONTEND_URL}/admin/leaders`)
    await expect(page.getByText('Pastor Schmidt')).toBeVisible({ timeout: 10000 })
  })
})
