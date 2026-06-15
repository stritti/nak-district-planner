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

test.describe('Calendar integrations admin view', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((auth) => {
      localStorage.setItem('auth', JSON.stringify(auth))
    }, ADMIN_AUTH)
  })

  test('renders calendar integrations', async ({ page }) => {
    await page.route('**/api/v1/calendar-integrations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'ci-1',
            name: 'ICS Kalender',
            type: 'ICS',
            district_id: 'district-1',
            is_active: true,
            sync_interval: 60,
          },
        ]),
      })
    })
    await page.route('**/api/v1/districts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ id: 'district-1', name: 'Bezirk München' }]),
      })
    })

    await page.goto(`${FRONTEND_URL}/admin/calendars`)
    await expect(page.getByRole('heading', { name: /Kalender/i })).toBeVisible({ timeout: 10000 })
  })
})
