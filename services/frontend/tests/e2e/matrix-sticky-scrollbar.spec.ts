import { expect, test } from '@playwright/test'
import { FRONTEND_URL, matrixResponse, setupAuthAndMatrix } from './helpers'

/** 40 congregations x 30 days: wider and taller than a small screen. */
function bigMatrix() {
  const base = matrixResponse({ isGap: false })
  const dates = Array.from({ length: 30 }, (_, i) => `2026-04-${String(i + 1).padStart(2, '0')}`)
  const cell = Object.values(base.rows[0].cells)[0]
  return {
    ...base,
    dates,
    rows: Array.from({ length: 40 }, (_, i) => ({
      ...base.rows[0],
      congregation_id: `cong-${i}`,
      congregation_name: `Gemeinde ${i}`,
      cells: Object.fromEntries(dates.map((d) => [d, { ...cell, event_id: `e-${i}-${d}` }])),
    })),
  }
}

test.describe('Matrix horizontal scrollbar', () => {
  test('stays at the bottom of the viewport and scrolls the table', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 600 })
    await setupAuthAndMatrix(page, bigMatrix())
    await page.goto(`${FRONTEND_URL}/matrix`)

    const scroll = page.getByTestId('matrix-scroll')
    const bar = page.getByTestId('matrix-sticky-scrollbar')
    await expect(scroll).toBeVisible({ timeout: 10000 })
    await expect(bar).toBeVisible()

    // The table is far taller than the screen, yet the bar is inside the viewport.
    const table = await scroll.boundingBox()
    expect(table!.height).toBeGreaterThan(600)
    const box = await bar.boundingBox()
    expect(box!.y + box!.height).toBeLessThanOrEqual(600 + 1)
    expect(box!.y).toBeGreaterThanOrEqual(0)

    // Dragging the bar scrolls the table horizontally, and the bar stays visible after scrolling down.
    await bar.evaluate((el) => { el.scrollLeft = 400 })
    await expect.poll(() => scroll.evaluate((el) => el.scrollLeft)).toBe(400)
    await page.mouse.wheel(0, 1500)
    const after = await bar.boundingBox()
    expect(after!.y + after!.height).toBeLessThanOrEqual(600 + 1)
    expect(after!.y).toBeGreaterThanOrEqual(0)
  })

  test('is hidden when the table fits', async ({ page }) => {
    await page.setViewportSize({ width: 1600, height: 900 })
    await setupAuthAndMatrix(page, matrixResponse({ isGap: false }))
    await page.goto(`${FRONTEND_URL}/matrix`)
    await expect(page.getByTestId('matrix-scroll')).toBeVisible({ timeout: 10000 })
    await expect(page.getByTestId('matrix-sticky-scrollbar')).toBeHidden()
  })
})
