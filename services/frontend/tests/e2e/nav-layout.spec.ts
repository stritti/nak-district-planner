// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect, test, type Page } from '@playwright/test'
import { mockAuthenticatedSession } from './helpers'

const IDENTITY = {
  sub: 'admin-1',
  email: 'stephan@st-strittmatter.name',
  name: 'Stephan Strittmatter',
}

async function openAsSuperadminWithPendingRegistration(page: Page, width: number) {
  await page.setViewportSize({ width, height: 700 })
  await page.emulateMedia({ colorScheme: 'dark' })
  // Catch-all registered FIRST → lowest priority (runs last in Playwright's reverse order)
  await page.route('**/api/v1/**', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }),
  )
  await mockAuthenticatedSession(page, IDENTITY)
  await page.route('**/api/v1/auth/me', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ...IDENTITY, username: 'stephan', is_superadmin: true }),
    }),
  )
  await page.route('**/api/v1/auth/access', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ACTIVE', memberships: [] }),
    }),
  )
  await page.route('**/api/v1/registrations/pending-overview', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total_pending: 1, by_district: [] }),
    }),
  )
  await page.goto('/events')
  await expect(page.locator('nav').getByText(IDENTITY.name).first()).toBeVisible()
}

/** Pairs of visible nav controls whose boxes intersect (ignores parent/child). */
async function overlappingControls(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const nav = document.querySelector('nav')
    if (!nav) return ['no nav']
    const items = [...nav.querySelectorAll<HTMLElement>('a, button, span')]
      .filter((el) => !el.closest('.fixed') && el.getClientRects().length > 0)
      .map((el) => ({ el, box: el.getBoundingClientRect(), label: (el.textContent ?? '').trim().slice(0, 24) }))
      .filter(({ box }) => box.width > 0 && box.height > 0)
    const found = new Set<string>()
    for (let i = 0; i < items.length; i++) {
      for (let j = i + 1; j < items.length; j++) {
        const a = items[i]
        const b = items[j]
        if (a.el.contains(b.el) || b.el.contains(a.el)) continue
        const overlapX = Math.min(a.box.right, b.box.right) - Math.max(a.box.left, b.box.left)
        const overlapY = Math.min(a.box.bottom, b.box.bottom) - Math.max(a.box.top, b.box.top)
        if (overlapX > 2 && overlapY > 2) found.add(`${a.label || '·'} × ${b.label || '·'}`)
      }
    }
    return [...found]
  })
}

test.describe('Navigation layout', () => {
  for (const width of [800, 1100, 1280, 1440, 1920]) {
    test(`controls do not overlap at ${width}px`, async ({ page }) => {
      await openAsSuperadminWithPendingRegistration(page, width)
      expect(await overlappingControls(page)).toEqual([])
    })
  }

  test('status badges stay on one line next to the links on desktop', async ({ page }) => {
    await openAsSuperadminWithPendingRegistration(page, 1280)
    const badge = page.getByRole('link', { name: /Registrierungen offen/ })
    await expect(badge).toBeVisible()
    await expect(page.locator('nav').getByText('Superadmin', { exact: true })).toBeVisible()
    // A wrapped label would be roughly twice as tall as a single line pill.
    const box = await badge.boundingBox()
    expect(box?.height ?? 99).toBeLessThan(30)
  })

  test('below xl the links move to the hamburger drawer', async ({ page }) => {
    await openAsSuperadminWithPendingRegistration(page, 1100)
    await expect(page.getByRole('link', { name: 'Ereignisse' })).toBeHidden()
    await page.getByRole('button', { name: 'Navigation öffnen' }).click()
    await expect(page.getByRole('link', { name: 'Ereignisse' })).toBeVisible()
    await expect(page.getByRole('link', { name: /Registrierungen offen/ })).toBeVisible()
  })
})
