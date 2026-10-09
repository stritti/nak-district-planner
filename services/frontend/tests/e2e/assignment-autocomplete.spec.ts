import { expect, test } from '@playwright/test'
import { FRONTEND_URL, matrixResponse, setupAuthAndMatrix } from './helpers'

const LEADERS = Array.from({ length: 80 }, (_, i) => ({
  id: `leader-${i}`,
  name: `Bruder Nummer ${String(i).padStart(2, '0')}`,
  district_id: 'district-1',
  rank: null,
  congregation_id: null,
  special_role: null,
  user_sub: null,
  email: null,
  phone: null,
  notes: null,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}))

test.describe('Leader autocomplete in the assignment modal', () => {
  test('stays inside the viewport with a long list and picks the best match', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 560 })
    await setupAuthAndMatrix(page, matrixResponse({ isGap: true }))
    await page.route(/\/api\/v1\/districts\/district-1\/leaders(?:\?.*)?$/, (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(LEADERS) }),
    )

    await page.goto(`${FRONTEND_URL}/matrix`)
    await page.getByRole('button', { name: /LÜCKE/i }).click({ timeout: 10000 })

    const input = page.getByPlaceholder(/Name eingeben/i)
    await input.click()
    const list = page.getByRole('listbox')
    await expect(list).toBeVisible()

    // The 80 entries never push the list outside the screen.
    const box = (await list.boundingBox())!
    expect(box.y).toBeGreaterThanOrEqual(0)
    expect(box.y + box.height).toBeLessThanOrEqual(560)
    expect(box.height).toBeLessThanOrEqual(180)

    // Typing pre-selects the first match; Enter takes it.
    await input.fill('nummer 07')
    await expect(list.getByRole('option', { selected: true })).toHaveText(/Bruder Nummer 07/)
    await input.press('Enter')
    await expect(input).toHaveValue('Bruder Nummer 07')
  })
})
