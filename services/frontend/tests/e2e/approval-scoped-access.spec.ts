// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { test, expect } from '@playwright/test'
import { mockAuthenticatedSession } from './helpers'

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Pending approval and scoped access UX', () => {
  test('shows pending approval banner when authenticated user has no memberships', async ({ page }) => {
    await page.route('**/api/v1/**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sub: 'pending-user',
          email: 'pending@example.com',
          name: 'Pending User',
          is_superadmin: false,
        }),
      })
    })
    await page.route('**/api/v1/auth/access', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'PENDING_APPROVAL', memberships: [] }),
      })
    })
    await mockAuthenticatedSession(page, {
      sub: 'pending-user',
      email: 'pending@example.com',
      name: 'Pending User',
    })

    await page.goto(`${FRONTEND_URL}/events`)
    await expect(
      page.getByText('Freigabe ausstehend: Ihr Konto ist angemeldet, aber noch keinem Bezirk oder keiner Gemeinde zugeordnet.'),
    ).toBeVisible()
  })
})
