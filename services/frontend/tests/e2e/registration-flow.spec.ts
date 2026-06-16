import { expect, test } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Public registration flow', () => {
  test('renders registration form without auth', async ({ page }) => {
    await page.route('**/api/v1/public/districts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ id: 'd1', name: 'Bezirk München' }]),
      })
    })

    await page.goto(`${FRONTEND_URL}/register`)
    // Registration page should be accessible without login
    await expect(page.getByRole('heading', { name: /Bezirksplaner/i })).toBeVisible({ timeout: 10000 })
  })
})
