import { expect, test } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

const AUTH = {
  token: {
    accessToken: 'fake-access-token',
    idToken: 'fake-id-token',
    expiresAt: Math.floor(Date.now() / 1000) + 3600,
  },
  user: { sub: 'planner-1', email: 'planner@example.com', name: 'Planner' },
  isSuperadmin: false,
  accessStatus: 'ACTIVE' as const,
  memberships: [
    { role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' },
  ],
}

test.describe('Event list CRUD', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((auth) => {
      localStorage.setItem('auth', JSON.stringify(auth))
    }, JSON.stringify(AUTH))
  })

  test('renders event list with mocked data', async ({ page }) => {
    await page.route('**/api/v1/events**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'ev-1',
            title: 'Gottesdienst',
            start_at: '2026-06-01T10:00:00Z',
            end_at: '2026-06-01T12:00:00Z',
            district_id: 'district-1',
            category: 'Gottesdienst',
            status: 'PUBLISHED',
            source: 'INTERNAL',
            visibility: 'INTERNAL',
          },
        ]),
      })
    })
    await page.route('**/api/v1/districts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ id: 'district-1', name: 'Bezirk Test' }]),
      })
    })

    await page.goto(`${FRONTEND_URL}/events`)
    await expect(page.getByText('Gottesdienst')).toBeVisible({ timeout: 10000 })
  })
})
