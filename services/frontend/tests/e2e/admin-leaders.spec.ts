import { expect, test } from '@playwright/test'
import { mockAuthenticatedSession } from './helpers'

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Leaders admin view', () => {
  test('renders leaders list and allows adding', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sub: 'admin-1', email: 'admin@example.com', name: 'Admin', is_superadmin: true,
        }),
      })
    })
    await page.route('**/api/v1/auth/access', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ACTIVE',
          memberships: [{ role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'district-1' }],
        }),
      })
    })
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
    await page.route('**/api/v1/districts/*/congregations', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })
    await page.route('**/api/v1/districts/*/self-link', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ leader: null }) })
    })
    await mockAuthenticatedSession(page, {
      sub: 'admin-1', email: 'admin@example.com', name: 'Admin',
    })

    await page.goto(`${FRONTEND_URL}/admin/leaders`)
    await expect(page.getByRole('cell', { name: 'Pastor Schmidt' })).toBeVisible({ timeout: 10000 })
  })
})
