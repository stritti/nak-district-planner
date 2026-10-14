// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect, test } from '@playwright/test'

import { FRONTEND_URL, mockAuthenticatedSession } from './helpers'

test.describe('Leader unavailabilities admin', () => {
  test.beforeEach(async ({ page }) => {
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
    await page.route('**/api/v1/registrations/pending-overview', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total_pending: 0 }),
      })
    })
    await mockAuthenticatedSession(page, {
      sub: 'admin-1',
      email: 'admin@example.com',
      name: 'Admin',
    })
  })

  test('records a new unavailability and shows it in the list', async ({ page }) => {
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
            rank: 'Pr.',
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
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ leader: null }),
      })
    })
    let createdCount = 0
    await page.route('**/api/v1/districts/*/leader-unavailabilities', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        })
        return
      }
      createdCount++
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'unavail-1',
          leader_id: 'leader-1',
          start_at: '2026-05-01T00:00:00.000Z',
          end_at: '2026-05-10T23:59:00.000Z',
          reason: 'URLAUB',
          note: 'Familienurlaub',
          created_at: '2026-04-01T00:00:00.000Z',
          updated_at: '2026-04-01T00:00:00.000Z',
        }),
      })
    })

    await page.goto(`${FRONTEND_URL}/admin/leaders`)
    await expect(page.getByRole('cell', { name: 'Pastor Schmidt' })).toBeVisible({ timeout: 10000 })

    await page.getByTestId('unavailability-tab').click()
    await expect(page.getByText('Keine Abwesenheiten erfasst.')).toBeVisible()

    await page.getByTestId('unavailability-start-date').fill('2026-05-01')
    await page.getByTestId('unavailability-end-date').fill('2026-05-10')
    await page.getByTestId('unavailability-reason-select').selectOption('URLAUB')
    await page.getByTestId('unavailability-note-input').fill('Familienurlaub')
    await page.getByTestId('unavailability-submit').click()

    await expect(page.getByTestId('unavailability-table')).toBeVisible()
    await expect(page.getByText('Familienurlaub')).toBeVisible()
    expect(createdCount).toBe(1)
  })

  test('opens the unavailabilities tab with a preset leader from the leaders tab', async ({
    page,
  }) => {
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
            rank: 'Pr.',
            is_active: true,
            congregation_id: null,
            district_id: 'district-1',
          },
          {
            id: 'leader-2',
            name: 'Diakon Weber',
            rank: 'Di.',
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
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ leader: null }),
      })
    })
    await page.route('**/api/v1/districts/*/leader-unavailabilities', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.goto(`${FRONTEND_URL}/admin/leaders`)
    await expect(page.getByRole('cell', { name: 'Pastor Schmidt' })).toBeVisible({ timeout: 10000 })

    await page
      .getByRole('row', { name: /Pastor Schmidt/ })
      .getByTitle('Abwesenheiten verwalten')
      .click()

    await expect(page.getByTestId('unavailability-table')).toBeHidden()
    await expect(page.getByTestId('unavailability-filter-select')).toHaveValue('leader-1')
  })

  test('client-side validation rejects an inverted period', async ({ page }) => {
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
            rank: 'Pr.',
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
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ leader: null }),
      })
    })
    await page.route('**/api/v1/districts/*/leader-unavailabilities', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.goto(`${FRONTEND_URL}/admin/leaders`)
    await expect(page.getByRole('cell', { name: 'Pastor Schmidt' })).toBeVisible({ timeout: 10000 })

    await page.getByTestId('unavailability-tab').click()
    await page.getByTestId('unavailability-start-date').fill('2026-05-10')
    await page.getByTestId('unavailability-end-date').fill('2026-05-01')
    await page.getByTestId('unavailability-reason-select').selectOption('URLAUB')
    await page.getByTestId('unavailability-submit').click()

    await expect(page.getByTestId('unavailability-form-error')).toContainText(
      'Das Ende muss nach dem Beginn liegen.',
    )
  })
})
