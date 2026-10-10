import { expect, test } from '@playwright/test'
import { matrixResponse, setupAuthAndMatrix } from './helpers'

test('global district selection is shown only when meaningful and shared by events and matrix', async ({ page }) => {
  await setupAuthAndMatrix(page, matrixResponse({ isGap: true }))
  const districtCalls: string[] = []

  await page.route('**/api/v1/auth/access', async (route) => {
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        status: 'ACTIVE',
        memberships: [
          { role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' },
          { role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-2' },
        ],
      }),
    })
  })
  await page.route('**/api/v1/districts', async (route) => {
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify([
        { id: 'district-1', name: 'Tuttlingen' },
        { id: 'district-2', name: 'Konstanz' },
      ]),
    })
  })
  await page.route(/\/api\/v1\/events(?:\?.*)?$/, async (route) => {
    const url = new URL(route.request().url())
    districtCalls.push(url.searchParams.get('district_id') ?? '')
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }),
    })
  })
  await page.route(/\/api\/v1\/districts\/district-2\/matrix(?:\?.*)?$/, async (route) => {
    districtCalls.push('matrix-2')
    await route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify(matrixResponse({ isGap: true })),
    })
  })

  await page.goto('http://localhost:5173/events')
  const select = page.getByRole('combobox', { name: 'Aktiven Bezirk wechseln' })
  await expect(select).toBeVisible()
  await expect(select).toHaveValue('district-1')
  await expect(page.locator('main h1').first()).toBeVisible()
  await expect(page.locator('.filter-bar').getByText('Bezirk', { exact: true })).toHaveCount(0)

  await select.selectOption('district-2')
  await expect(select).toHaveValue('district-2')
  await expect.poll(() => districtCalls.includes('district-2')).toBe(true)

  await page.getByRole('link', { name: 'Dienstplan-Matrix' }).first().click()
  await expect(page.locator('main h1').first()).toBeVisible()
  await expect(select).toHaveValue('district-2')
  await expect(page.locator('.filter-bar').getByText('Bezirk', { exact: true })).toHaveCount(0)
  await expect.poll(() => districtCalls.includes('matrix-2')).toBe(true)
})

test('single district is clearly shown without a district switcher', async ({ page }) => {
  await setupAuthAndMatrix(page, matrixResponse({ isGap: true }))
  await page.goto('http://localhost:5173/matrix')
  await expect(page.getByLabel('Aktueller Bezirk: Bezirk 1')).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Aktiven Bezirk wechseln' })).toHaveCount(0)
  await expect(page.locator('.filter-bar').getByText('Bezirk', { exact: true })).toHaveCount(0)
})
