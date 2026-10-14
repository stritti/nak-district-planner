// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect, test, type Page } from '@playwright/test'
import { mockAuthenticatedSession } from './helpers'

const API = '**/api/v1/**'
const BASE = 'http://localhost:5173'

async function mockReadOnlyApi(page: Page): Promise<void> {
  await page.route(API, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
}

async function signIn(page: Page, role: 'VIEWER' | 'PLANNER', user: string): Promise<void> {
  await mockReadOnlyApi(page)
  await page.route('**/api/v1/auth/me', (route) => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ sub: user, email: `${user}@example.com`, name: user, is_superadmin: false }),
  }))
  await page.route('**/api/v1/auth/access', (route) => route.fulfill({
    status: 200, contentType: 'application/json',
    body: JSON.stringify({ status: 'ACTIVE', memberships: [{ role, scope_type: 'DISTRICT', scope_id: 'district-1' }] }),
  }))
  await mockAuthenticatedSession(page, {
    sub: user,
    email: `${user}@example.com`,
    name: user,
  })
}

test.describe('contextual help', () => {
  test('guest guidance supports hide, reload, and restore on the registration page', async ({ page }) => {
    await mockReadOnlyApi(page)
    await page.goto(`${BASE}/register`)
    const help = page.getByRole('region', { name: 'Kontextuelle Hilfe' })
    await expect(help).toBeVisible()
    await expect(help.getByText('Registrierung', { exact: true })).toBeVisible()
    await help.getByRole('button', { name: 'Anzeigen' }).click()
    await expect(help.getByText('Wähle deinen Bezirk und gib deine Kontaktdaten an.')).toBeVisible()
    await help.getByRole('button', { name: 'Registrierung ausblenden' }).click()
    await page.reload()
    await expect(help.getByText('Registrierung', { exact: true })).toBeHidden()
    await help.getByRole('button', { name: 'Ausgeblendete Hilfe wiederherstellen' }).click()
    await expect(help.getByText('Registrierung', { exact: true })).toBeVisible()
  })

  test('viewer receives only viewer guidance on events, not planner guidance on matrix', async ({ page }) => {
    await signIn(page, 'VIEWER', 'viewer-e2e')
    await page.goto(`${BASE}/events`)
    const help = page.getByRole('region', { name: 'Kontextuelle Hilfe' })
    await expect(help.getByText('Ereignisse finden')).toBeVisible()
    await expect(help.getByText('Ereignisse planen')).toHaveCount(0)
    await page.goto(`${BASE}/matrix`)
    await expect(page.getByText('Mit der Dienstplan-Matrix arbeiten')).toHaveCount(0)
  })

  test('planner sees planning guidance in both contexts and retains hidden status', async ({ page }) => {
    await signIn(page, 'PLANNER', 'planner-e2e')
    await page.goto(`${BASE}/events`)
    const help = page.getByRole('region', { name: 'Kontextuelle Hilfe' })
    await expect(help.getByText('Ereignisse planen')).toBeVisible()
    await expect(help.getByText('Ereignisse finden')).toHaveCount(0)
    await help.getByRole('button', { name: 'Ereignisse planen ausblenden' }).click()
    await page.reload()
    await expect(help.getByText('Ereignisse planen')).toHaveCount(0)
    await help.getByRole('button', { name: 'Ausgeblendete Hilfe wiederherstellen' }).click()
    await expect(help.getByText('Ereignisse planen')).toBeVisible()
    await page.goto(`${BASE}/matrix`)
    await expect(page.getByText('Mit der Dienstplan-Matrix arbeiten')).toBeVisible()
  })
})
