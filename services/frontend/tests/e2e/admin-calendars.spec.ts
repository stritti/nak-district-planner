// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect, test } from '@playwright/test'
import { mockAuthenticatedSession } from './helpers'

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Calendar integrations admin view', () => {
  test('renders calendar integrations', async ({ page }) => {
    // Catch-all registered FIRST → lowest priority (runs last in Playwright's reverse order)
    await page.route('**/api/v1/**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sub: 'admin-1',
          email: 'admin@example.com',
          username: 'admin',
          name: 'Admin',
          is_superadmin: true,
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
            { role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'district-1' },
          ],
        }),
      })
    })
    await page.route('**/api/v1/registrations/pending/overview', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total_pending: 0 }),
      })
    })
    // The view filters by the selected district (`?district_id=…`); a plain glob
    // would not match the query string and fall through to the catch-all.
    await page.route(/\/api\/v1\/calendar-integrations(\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'ci-1',
              name: 'ICS Kalender',
              type: 'ICS',
              district_id: 'district-1',
              is_active: true,
              sync_interval: 60,
              congregation_id: null,
              capabilities: ['READ'],
              last_synced_at: null,
              created_at: '2026-06-01T00:00:00Z',
              updated_at: '2026-06-01T00:00:00Z',
              default_category: null,
            },
          ],
          total: 1,
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
    await mockAuthenticatedSession(page, {
      sub: 'admin-1',
      email: 'admin@example.com',
      name: 'Admin',
    })

    await page.goto(`${FRONTEND_URL}/admin/calendars`)
    await expect(page.getByRole('heading', { name: /Kalender/i })).toBeVisible({ timeout: 10000 })
  })
})
