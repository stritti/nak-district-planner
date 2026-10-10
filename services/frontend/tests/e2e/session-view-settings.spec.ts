// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect, test, type Page } from '@playwright/test'
import { FRONTEND_URL, matrixResponse, setupAuthAndMatrix } from './helpers'

test.use({ viewport: { width: 1440, height: 900 } })

async function prepare(page: Page) {
  await setupAuthAndMatrix(page, matrixResponse({ isGap: true }))
  await page.route(/\/api\/v1\/events(?:\?.*)?$/, async (route) => {
    const query = new URL(route.request().url()).searchParams
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        items: [{
          id: 'session-event', title: query.get('status') === 'CANCELLED' ? 'Abgesagt gefiltert' : 'Alle Ereignisse',
          start_at: '2026-10-05T09:30:00', end_at: '2026-10-05T10:30:00',
          district_id: 'district-1', congregation_id: null, category: null,
          is_service: false, source: 'INTERNAL', status: query.get('status') || 'ACTIVE',
          approval_status: 'CONFIRMED', visibility: 'INTERNAL', applicability: [],
          description: null, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z',
        }],
        total: 1, limit: 50, offset: 0,
      }),
    })
  })
}

const nav = (page: Page, path: string) => page.locator('nav a[href="' + path + '"]:visible').first()

test('matrix and event filters survive view navigation, history and reload independently', async ({ page }) => {
  await prepare(page)
  await page.goto(FRONTEND_URL + '/matrix')
  await page.locator('#matrix-congregation-filter').fill('Gemeinde A')
  await page.locator('#matrix-sort-filter').selectOption('grouped')
  await nav(page, '/events').click()
  await page.locator('#event-status-filter').selectOption('CANCELLED')
  await page.locator('#event-approval-filter').selectOption('CONFIRMED')
  await expect(page.getByText('Abgesagt gefiltert').filter({ visible: true }).first()).toBeVisible()
  await nav(page, '/matrix').click()
  await expect(page.locator('#matrix-congregation-filter')).toHaveValue('Gemeinde A')
  await expect(page.locator('#matrix-sort-filter')).toHaveValue('grouped')

  await page.goBack()
  await expect(page.locator('#event-status-filter')).toHaveValue('CANCELLED')
  await expect(page.locator('#event-approval-filter')).toHaveValue('CONFIRMED')
  await expect(page.getByText('Abgesagt gefiltert').filter({ visible: true }).first()).toBeVisible()
  await page.reload()
  await expect(page.locator('#event-status-filter')).toHaveValue('CANCELLED')
  await expect(page.getByText('Abgesagt gefiltert').filter({ visible: true }).first()).toBeVisible()
  await nav(page, '/matrix').click()
  await page.reload()
  await expect(page.locator('#matrix-sort-filter')).toHaveValue('grouped')
  await expect(page.locator('#matrix-congregation-filter')).toHaveValue('Gemeinde A')
  await page.goBack()
  await page.goForward()
  await expect(page.locator('#matrix-sort-filter')).toHaveValue('grouped')
})

test('an independent tab starts with defaults and explicit clearing is retained', async ({ page, context }) => {
  await prepare(page)
  await page.goto(FRONTEND_URL + '/matrix')
  await page.locator('#matrix-congregation-filter').fill('Gemeinde A')
  await page.locator('#matrix-sort-filter').selectOption('grouped')
  const fresh = await context.newPage()
  await prepare(fresh)
  await fresh.goto(FRONTEND_URL + '/matrix')
  await expect(fresh.locator('#matrix-congregation-filter')).toHaveValue('')
  await expect(fresh.locator('#matrix-sort-filter')).toHaveValue('default')
  await fresh.close()
  await page.locator('#matrix-congregation-filter').fill('')
  await page.locator('#matrix-sort-filter').selectOption('default')
  await nav(page, '/events').click()
  await nav(page, '/matrix').click()
  await expect(page.locator('#matrix-congregation-filter')).toHaveValue('')
  await expect(page.locator('#matrix-sort-filter')).toHaveValue('default')
})
