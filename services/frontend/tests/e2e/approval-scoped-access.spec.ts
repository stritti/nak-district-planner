import { test, expect } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Pending approval and scoped access UX', () => {
  test('shows pending approval banner when authenticated user has no memberships', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem(
        'auth',
        JSON.stringify({
          token: {
            accessToken: 'fake-access-token',
            idToken: 'fake-id-token',
            expiresAt: Math.floor(Date.now() / 1000) + 3600,
          },
          user: {
            sub: 'pending-user',
            email: 'pending@example.com',
            name: 'Pending User',
          },
          isSuperadmin: false,
          accessStatus: 'PENDING_APPROVAL',
          memberships: [],
        }),
      )
    })

    await page.goto(`${FRONTEND_URL}/events`)
    await expect(
      page.getByText('Freigabe ausstehend: Ihr Konto ist angemeldet, aber noch keinem Bezirk oder keiner Gemeinde zugeordnet.'),
    ).toBeVisible()
  })
})
