import { expect, test, type Locator } from '@playwright/test'
import { FRONTEND_URL, matrixResponse, setupAuthAndMatrix } from './helpers'

/** Checks opacity by rendering the CSS color, independently of rgb/oklch serialization. */
async function backgroundAlpha(element: Locator): Promise<number> {
  return element.evaluate((node) => {
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    if (!context) throw new Error('Canvas 2D context unavailable')
    context.fillStyle = getComputedStyle(node).backgroundColor
    context.fillRect(0, 0, 1, 1)
    return context.getImageData(0, 0, 1, 1).data[3]
  })
}

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
    await expect.poll(() => scroll.evaluate((el) => Math.abs(el.scrollLeft - 400))).toBeLessThanOrEqual(3)
    await page.mouse.wheel(0, 1500)
    const after = await bar.boundingBox()
    expect(after!.y + after!.height).toBeLessThanOrEqual(600 + 1)
    expect(after!.y).toBeGreaterThanOrEqual(0)
  })

  test('reaches the final column with a classic vertical scrollbar', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 600 })
    await setupAuthAndMatrix(page, bigMatrix())
    await page.goto(`${FRONTEND_URL}/matrix`)
    // Even on systems with overlay scrollbars, reserve the classic scrollbar gutter.
    await page.addStyleTag({ content: '[data-testid="matrix-scroll"] { scrollbar-gutter: stable; }' })
    const scroll = page.getByTestId('matrix-scroll')
    const proxy = page.getByTestId('matrix-sticky-scrollbar')
    await expect(proxy).toBeVisible()

    await expect.poll(() => scroll.evaluate((element) =>
      element.getBoundingClientRect().width - element.clientWidth,
    )).toBeGreaterThan(0)
    await expect.poll(async () => {
      const widths = await Promise.all([scroll, proxy].map((item) =>
        item.evaluate((element) => element.clientWidth),
      ))
      return Math.abs(widths[0] - widths[1])
    }).toBeLessThanOrEqual(1)

    // Chromium can reserve a scrollbar gutter inside scrollWidth. In that
    // case scrollWidth - clientWidth is larger than the *reachable* native
    // scrollLeft maximum, so compare the two actual endpoints instead.
    const nativeEnd = await scroll.evaluate((element) => {
      element.scrollLeft = element.scrollWidth
      const end = element.scrollLeft
      element.scrollLeft = 0
      return end
    })
    await expect.poll(() => scroll.evaluate((element) => element.scrollLeft)).toBe(0)
    await proxy.evaluate((element) => { element.scrollLeft = element.scrollWidth })
    await expect.poll(() => scroll.evaluate((element) =>
      Math.abs(nativeEnd - element.scrollLeft),
    )).toBeLessThanOrEqual(1)

    const lastColumn = await scroll.evaluate((element) => {
      const right = element.getBoundingClientRect().right
      const lastDate = element.querySelector('thead th:last-child')!.getBoundingClientRect()
      return { left: lastDate.left, right: lastDate.right, viewportRight: right }
    })
    expect(lastColumn.left).toBeLessThan(lastColumn.viewportRight)
    expect(lastColumn.right).toBeLessThanOrEqual(lastColumn.viewportRight + 1)
  })

  test('passes vertical wheel scrolling to the page at the matrix boundary', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await setupAuthAndMatrix(page, bigMatrix())
    await page.goto(`${FRONTEND_URL}/matrix`)
    const scroll = page.getByTestId('matrix-scroll')
    await expect(scroll).toBeVisible({ timeout: 10000 })
    expect(await scroll.evaluate((element) => getComputedStyle(element).overscrollBehaviorX)).toBe('contain')
    expect(await scroll.evaluate((element) => getComputedStyle(element).overscrollBehaviorY)).toBe('auto')

    // Ensure that the document can scroll further after the matrix.
    await page.evaluate(() => { document.body.style.paddingBottom = '1200px' })
    await scroll.hover({ position: { x: 25, y: 50 } })
    await scroll.evaluate((element) => { element.scrollTop = element.scrollHeight })
    const before = await page.evaluate(() => window.scrollY)
    await page.mouse.wheel(0, 400)
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(before)
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
    const fixture = bigMatrix()
    fixture.holidays = { '2026-04-10': ['Langer Gedenktag'] }
    await setupAuthAndMatrix(page, fixture)
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
    expect(await backgroundAlpha(corner)).toBe(255)
    const holiday = scroll.locator('thead th').nth(10)
    expect(await backgroundAlpha(holiday)).toBe(255)
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
