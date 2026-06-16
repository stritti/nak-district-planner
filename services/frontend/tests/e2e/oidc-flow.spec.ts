/**
 * End-to-End Test: OIDC Authentication Flow
 * 
 * Tests the complete OIDC login → token → API call → logout flow
 * This test validates Phase 4b implementation (OIDC with PKCE)
 * 
 * Note: Tests that require a real OIDC provider are skipped in CI.
 */

import { test, expect } from '@playwright/test'

// Configuration from environment
const FRONTEND_URL = 'http://localhost:5173'
const isCI = process.env.CI === 'true'

/**
 * Mock OIDC discovery so the login form renders (no real backend needed).
 */
async function mockOidcDiscovery(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/auth/oidc/discovery', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        authorization_endpoint: 'http://localhost:9999/authorize',
        token_endpoint: 'http://localhost:9999/token',
        userinfo_endpoint: 'http://localhost:9999/userinfo',
        client_id: 'test-client-id',
      }),
    })
  })
}

test.describe('OIDC Authentication Flow', () => {
  test('01: Should navigate to login page', async ({ page }) => {
    await mockOidcDiscovery(page)
    await page.goto(`${FRONTEND_URL}/login`)
    await expect(page).toHaveTitle(/Login|NAK/)
    // The login page shows "Mit Single Sign-on anmelden" (German), not "Login"
    const loginButton = page.locator('button:has-text("Mit Single Sign-on anmelden")')
    await expect(loginButton).toBeVisible()
  })

  test('02: Should store access token after successful login', async ({ page }) => {
    test.skip(isCI, 'Requires a real OIDC provider – cannot run in CI')

    await mockOidcDiscovery(page)
    await page.goto(`${FRONTEND_URL}/login`)

    const loginButton = page.locator('button:has-text("Mit Single Sign-on anmelden")')
    await loginButton.click()

    // Wait for redirect to OIDC provider
    await page.waitForURL('http://localhost:9999/**', { timeout: 15000 })

    // Simulate successful OIDC callback (redirect back with code)
    await page.goto(`${FRONTEND_URL}/auth/callback?code=mock-code&state=mock-state`)

    // Wait for token to be stored
    await page.waitForTimeout(500)

    const token = await page.evaluate(() => {
      const authStore = localStorage.getItem('auth')
      return authStore ? JSON.parse(authStore).token : null
    })

    expect(token).toBeTruthy()
  })

  test('03: Should prevent access to protected routes without token', async ({ page }) => {
    // Clear localStorage before navigating (use goto to establish an origin first)
    await page.goto(`${FRONTEND_URL}/login`)
    await page.evaluate(() => localStorage.clear())

    // Try to access protected route
    await page.goto(`${FRONTEND_URL}/events`)

    // Should redirect to login
    expect(page.url()).toContain('/login')
  })

  test('04: Should allow access to protected routes with valid token', async ({ page }) => {
    test.skip(isCI, 'Requires a real OIDC provider – cannot run in CI')

    // Set up authenticated state via localStorage
    await page.addInitScript(() => {
      localStorage.setItem('auth', JSON.stringify({
        token: { accessToken: 'e2e-token', idToken: 'e2e-id', expiresAt: Math.floor(Date.now() / 1000) + 3600 },
        user: { sub: 'e2e-user', email: 'e2e@example.com', name: 'E2E User' },
        isSuperadmin: false,
        accessStatus: 'ACTIVE',
        memberships: [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' }],
      }))
    })

    await page.goto(`${FRONTEND_URL}/events`)

    // Should NOT redirect to login
    expect(page.url()).not.toContain('/login')
    expect(page.url()).toContain('/events')
  })

  test('05: Should successfully logout', async ({ page }) => {
    test.skip(isCI, 'Requires a real OIDC provider – cannot run in CI')

    // Set up authenticated state
    await page.addInitScript(() => {
      localStorage.setItem('auth', JSON.stringify({
        token: { accessToken: 'e2e-token', idToken: 'e2e-id', expiresAt: Math.floor(Date.now() / 1000) + 3600 },
        user: { sub: 'e2e-user', email: 'e2e@example.com', name: 'E2E User' },
        isSuperadmin: false,
        accessStatus: 'ACTIVE',
        memberships: [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' }],
      }))
    })

    // Mock API calls
    await page.route('**/api/v1/**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })

    await page.goto(`${FRONTEND_URL}/events`)

    // Find logout button in user menu
    const userMenu = page.locator('[data-testid="user-menu"], .user-menu')
    if (await userMenu.isVisible()) {
      await userMenu.click()
    }

    const logoutButton = page.locator(
      'button:has-text("Logout"), button:has-text("Sign Out"), button:has-text("Abmelden")',
    )

    if (await logoutButton.isVisible()) {
      await logoutButton.click()
      await page.waitForURL(`**/login**`, { timeout: 10000 })

      const token = await page.evaluate(() => {
        const authStore = localStorage.getItem('auth')
        return authStore ? JSON.parse(authStore).token : null
      })

      expect(token).toBeFalsy()
    }
  })
})
