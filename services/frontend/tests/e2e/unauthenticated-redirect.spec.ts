import { expect, test } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Unauthenticated access', () => {
  test('redirects to login for protected routes', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/events`)
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 })
  })

  test('redirects to login for matrix route', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/matrix`)
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 })
  })

  test('redirects to login for admin routes', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/admin/districts`)
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 })
  })

  test('allows access to public registration page', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/register`)
    // Should NOT redirect to login
    expect(page.url()).not.toContain('/login')
  })
})
