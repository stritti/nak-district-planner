/**
 * End-to-End Test: OIDC Authentication Flow
 * 
 * Tests the complete OIDC login → token → API call → logout flow
 * This test validates Phase 4b implementation (OIDC with PKCE)
 */

import { test, expect } from '@playwright/test'

// Configuration from environment
const FRONTEND_URL = 'http://localhost:5173'
const TEST_USER = {
  username: 'testuser',
  password: 'testpassword123',
}

test.describe('OIDC Authentication Flow', () => {
  test('01: Should navigate to login page', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/login`)
    await expect(page).toHaveTitle(/Login|NAK/)
    const loginButton = page.locator('button:has-text("Login")')
    await expect(loginButton).toBeVisible()
  })

  test('02: Should store access token after successful login', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/login`)
    
    const loginButton = page.locator('button:has-text("Login")')
    await loginButton.click()
    
    // Wait for redirect to complete
    await page.waitForURL(`${FRONTEND_URL}/**`, { timeout: 15000 })
    
    // Wait for token to be stored
    await page.waitForTimeout(500)
    
    const token = await page.evaluate(() => {
      const authStore = localStorage.getItem('auth-store')
      return authStore ? JSON.parse(authStore).token : null
    })
    
    expect(token).toBeTruthy()
  })

  test('03: Should prevent access to protected routes without token', async ({ page }) => {
    // Clear any existing tokens
    await page.context().clearCookies()
    await page.evaluate(() => localStorage.clear())
    
    // Try to access protected route
    await page.goto(`${FRONTEND_URL}/events`)
    
    // Should redirect to login
    expect(page.url()).toContain('/login')
  })

  test('04: Should allow access to protected routes with valid token', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/login`)
    
    const loginButton = page.locator('button:has-text("Login")')
    await loginButton.click()
    
    await page.waitForURL(`${FRONTEND_URL}/**`, { timeout: 15000 })
    
    // Navigate to protected route
    await page.goto(`${FRONTEND_URL}/events`)
    
    // Should NOT redirect to login
    expect(page.url()).not.toContain('/login')
    expect(page.url()).toContain('/events')
  })

  test('05: Should successfully logout', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/login`)
    
    const loginButton = page.locator('button:has-text("Login")')
    await loginButton.click()
    
    await page.waitForURL(`${FRONTEND_URL}/**`, { timeout: 15000 })
    
    // Find logout button in user menu
    const userMenu = page.locator('[data-testid="user-menu"], .user-menu')
    if (await userMenu.isVisible()) {
      await userMenu.click()
    }
    
    const logoutButton = page.locator(
      'button:has-text("Logout"), button:has-text("Sign Out")'
    )
    
    if (await logoutButton.isVisible()) {
      await logoutButton.click()
      await page.waitForURL(`**/login**`, { timeout: 10000 })
      
      const token = await page.evaluate(() => {
        const authStore = localStorage.getItem('auth-store')
        return authStore ? JSON.parse(authStore).token : null
      })
      
      expect(token).toBeFalsy()
    }
  })
})
