// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect, test, type Page } from '@playwright/test'
import { FRONTEND_URL, mockAuthenticatedSession } from './helpers'

async function mockLoggedOutSession(page: Page): Promise<void> {
  await page.route('**/api/v1/auth/oidc/discovery', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: { 'set-cookie': 'csrf_token=e2e-csrf; Path=/; SameSite=Strict' },
      body: JSON.stringify({
        authorization_endpoint: 'https://idp.example/authorize',
        token_endpoint: 'https://idp.example/token',
        userinfo_endpoint: 'https://idp.example/userinfo',
        client_id: 'planner-client',
      }),
    })
  })
  await page.route('**/api/v1/auth/oidc/token', async (route) => {
    expect(route.request().method()).toBe('POST')
    await route.fulfill({ status: 401, contentType: 'application/json', body: '{}' })
  })
}

async function mockAuthenticatedApi(page: Page): Promise<void> {
  // Register the broad fallback first so the specific routes below win.
  await page.route('**/api/v1/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        sub: 'e2e-user',
        email: 'e2e@example.com',
        username: 'e2e-user',
        name: 'E2E User',
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
        memberships: [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' }],
      }),
    })
  })
  await page.route('**/api/v1/system/version', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ version: 'e2e' }),
    })
  })
  await mockAuthenticatedSession(page, {
    sub: 'e2e-user',
    email: 'e2e@example.com',
    name: 'E2E User',
  })
}

test.describe('OIDC Authentication Flow', () => {
  test('shows the login page while no refresh session exists', async ({ page }) => {
    await mockLoggedOutSession(page)

    await page.goto(`${FRONTEND_URL}/login`)

    await expect(page.getByRole('button', { name: 'Mit Single Sign-on anmelden' })).toBeVisible()
  })

  test('restores access in memory without persisting browser auth credentials', async ({ page }) => {
    await mockAuthenticatedApi(page)

    await page.goto(`${FRONTEND_URL}/events`)

    await expect(page).toHaveURL(/\/events$/)
    await expect.poll(() => page.evaluate(() => localStorage.getItem('auth'))).toBeNull()
  })

  test('redirects protected routes to login when the server has no refresh session', async ({ page }) => {
    await mockLoggedOutSession(page)

    await page.goto(`${FRONTEND_URL}/events`)

    await expect(page).toHaveURL(/\/login$/)
  })

  test('allows protected navigation after a valid server-side session restore', async ({ page }) => {
    await mockAuthenticatedApi(page)

    await page.goto(`${FRONTEND_URL}/events`)

    await expect(page).toHaveURL(/\/events$/)
    await expect(page.getByText('E2E User', { exact: true }).first()).toBeVisible()
  })

  test('logs out locally and revokes the server-held refresh session', async ({ page }) => {
    await mockAuthenticatedApi(page)
    let revokeCalls = 0
    await page.route('**/api/v1/auth/oidc/revoke', async (route) => {
      revokeCalls += 1
      expect(route.request().method()).toBe('POST')
      expect(route.request().headers()['x-csrf-token']).toBe('e2e-csrf')
      await route.fulfill({ status: 204, body: '' })
    })

    await page.goto(`${FRONTEND_URL}/events`)
    await expect(page).toHaveURL(/\/events$/)
    await page.getByRole('button', { name: /E2E User/ }).click()
    await page.getByRole('button', { name: 'Abmelden' }).click()

    await expect(page).toHaveURL(/\/login$/)
    expect(revokeCalls).toBe(1)
    expect(await page.evaluate(() => localStorage.getItem('auth'))).toBeNull()
  })
})
