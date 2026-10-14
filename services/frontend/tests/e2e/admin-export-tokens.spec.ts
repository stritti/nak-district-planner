// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect, test } from '@playwright/test'
import { mockAuthenticatedSession } from './helpers'

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Export tokens view', () => {
  test('renders export tokens page', async ({ page }) => {
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
    await mockAuthenticatedSession(page, {
      sub: 'admin-1', email: 'admin@example.com', name: 'Admin',
    })

    await page.goto(`${FRONTEND_URL}/admin/export`)
    await expect(page.getByRole('heading', { name: /Export/i })).toBeVisible({ timeout: 10000 })
  })
})
