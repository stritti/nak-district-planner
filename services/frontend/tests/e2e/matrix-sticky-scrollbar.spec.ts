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

    // The matrix content is taller than the bounded scroll area; the proxy is still viewport-visible.
    const dimensions = await scroll.evaluate((el) => ({ height: el.clientHeight, fullHeight: el.scrollHeight }))
    expect(dimensions.fullHeight).toBeGreaterThan(600)
    expect(dimensions.fullHeight).toBeGreaterThan(dimensions.height)
    expect(dimensions.height).toBeLessThan(600)
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


test.describe('Matrix fixed date header', () => {
  test('keeps date headings and congregation names fixed when scrolling both axes', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 600 })
    const fixture = bigMatrix()
    fixture.holidays = { '2026-04-10': ['Besonders langer Feiertagsname'] }
    await setupAuthAndMatrix(page, fixture)
    await page.goto(`${FRONTEND_URL}/matrix`)

    const scroll = page.getByTestId('matrix-scroll')
    await expect(scroll).toBeVisible({ timeout: 10000 })
    const corner = scroll.locator('thead th').first()
    const day = scroll.locator('thead th').nth(10)
    const congregation = scroll.locator('tbody tr').first().locator('td').first()
    await expect(scroll.getByText('Besonders langer Feiertagsname')).toBeVisible()

    await scroll.evaluate((element) => { element.scrollTop = 900; element.scrollLeft = 800 })
    await expect.poll(() => scroll.evaluate((element) => element.scrollTop)).toBeGreaterThan(800)
    await expect.poll(() => scroll.evaluate((element) => element.scrollLeft)).toBeGreaterThan(700)

    const positions = await scroll.evaluate((element) => {
      const bounds = element.getBoundingClientRect()
      const headings = element.querySelectorAll('thead th')
      const corner = headings[0].getBoundingClientRect()
      const day = headings[10].getBoundingClientRect()
      const congregation = element.querySelector('tbody td')!.getBoundingClientRect()
      return {
        matrixTop: bounds.top,
        matrixLeft: bounds.left,
        cornerTop: corner.top,
        cornerLeft: corner.left,
        dateTop: day.top,
        congregationLeft: congregation.left,
      }
    })
    expect(Math.abs(positions.cornerTop - positions.matrixTop)).toBeLessThanOrEqual(2)
    expect(Math.abs(positions.dateTop - positions.matrixTop)).toBeLessThanOrEqual(2)
    expect(Math.abs(positions.cornerLeft - positions.matrixLeft)).toBeLessThanOrEqual(2)
    expect(Math.abs(positions.congregationLeft - positions.matrixLeft)).toBeLessThanOrEqual(2)
    const layers = await Promise.all([corner, day, congregation].map((locator) =>
      locator.evaluate((element) => Number(getComputedStyle(element).zIndex)),
    ))
    expect(layers[0]).toBeGreaterThan(layers[1])
    expect(layers[1]).toBeGreaterThan(layers[2])
  })

  test('keeps the header in the scroll region in compact dark mode', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await setupAuthAndMatrix(page, bigMatrix())
    await page.addInitScript(() => { localStorage.setItem('matrix.compactMode', '1') })
    await page.goto(`${FRONTEND_URL}/matrix`)
    await page.evaluate(() => { document.documentElement.classList.add('dark') })

    const scroll = page.getByTestId('matrix-scroll')
    await expect(scroll).toBeVisible({ timeout: 10000 })
    await scroll.evaluate((element) => { element.scrollTop = 700; element.scrollLeft = 400 })
    await expect.poll(() => scroll.evaluate((element) => element.scrollTop)).toBeGreaterThan(600)

    const corner = scroll.locator('thead th').first()
    const day = scroll.locator('thead th').nth(5)
    const top = await scroll.evaluate((element) => element.getBoundingClientRect().top)
    expect(Math.abs((await corner.boundingBox())!.y - top)).toBeLessThanOrEqual(2)
    expect(Math.abs((await day.boundingBox())!.y - top)).toBeLessThanOrEqual(2)
    expect(await corner.evaluate((element) => getComputedStyle(element).backgroundColor)).not.toBe('rgba(0, 0, 0, 0)')
  })

  test('does not add vertical scrolling for a short matrix', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 600 })
    await setupAuthAndMatrix(page, matrixResponse({ isGap: false }))
    await page.goto(`${FRONTEND_URL}/matrix`)
    const scroll = page.getByTestId('matrix-scroll')
    await expect(scroll).toBeVisible({ timeout: 10000 })
    expect(await scroll.evaluate((element) => element.scrollHeight <= element.clientHeight)).toBe(true)
  })
})
