import { expect, test } from '@playwright/test'
import { mockAuthenticatedSession } from './helpers'

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Event list CRUD', () => {
  test('renders event list with mocked data', async ({ page }) => {
    // Catch-all registered FIRST → lowest priority (runs last in Playwright's reverse order)
    await page.route('**/api/v1/**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sub: 'planner-1',
          email: 'planner@example.com',
          username: 'planner',
          name: 'Planner',
          given_name: 'Planner',
          family_name: '',
          is_superadmin: false,
        }),
      })
    })
    await page.route('**/api/v1/auth/access', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'ACTIVE',
          memberships: [
            { role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' },
          ],
        }),
      })
    })

    await page.route('**/api/v1/events**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
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
          ],
          total: 1,
          limit: 50,
          offset: 0,
        }),
      })
    })
    await page.route('**/api/v1/districts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ id: 'district-1', name: 'Bezirk Test' }]),
      })
    })
    await mockAuthenticatedSession(page, {
      sub: 'planner-1',
      email: 'planner@example.com',
      name: 'Planner',
    })

    await page.goto(`${FRONTEND_URL}/events`)
    await expect(page.getByRole('cell', { name: 'Gottesdienst' }).first()).toBeVisible({
      timeout: 10000,
    })
  })
})
