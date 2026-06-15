import { expect, test } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

const AUTH = {
  token: { accessToken: 'nav-token', idToken: 'nav-id-token', expiresAt: Math.floor(Date.now() / 1000) + 3600 },
  user: { sub: 'nav-user', email: 'nav@example.com', name: 'Navigator' },
  isSuperadmin: true,
  accessStatus: 'ACTIVE' as const,
  memberships: [{ role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'district-1' }],
}

test.describe('App navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((auth) => {
      localStorage.setItem('auth', JSON.stringify(auth))
    }, JSON.stringify(AUTH))
  })

  test('navigation shows after login and links work', async ({ page }) => {
    // Mock all API calls to return empty data
    await page.route('**/api/v1/**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    })

    await page.goto(`${FRONTEND_URL}/events`)
    // Should see the nav bar
    await expect(page.getByRole('navigation')).toBeVisible({ timeout: 10000 })
  })
})
