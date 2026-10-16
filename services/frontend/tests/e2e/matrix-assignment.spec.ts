// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect, test } from '@playwright/test'
import {
  EVENT_REVISION,
  FRONTEND_URL,
  UPDATED_EVENT_REVISION,
  matrixResponse,
  setupAuthAndMatrix,
} from './helpers'

test.describe('Matrix assignment flow', () => {
  test('gap can be assigned and turns into assigned cell', async ({ page }) => {
    let assignmentCreated = false
    const ifMatchHeaders: (string | undefined)[] = []

    await setupAuthAndMatrix(page, matrixResponse({ isGap: true }))

    await page.route(/\/api\/v1\/events\/event-1\/assignments(?:\?.*)?$/, async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback()
        return
      }
      assignmentCreated = true
      ifMatchHeaders.push(route.request().headers()['if-match'])
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'assignment-1',
          event_id: 'event-1',
          leader_id: null,
          leader_name: 'Pr. Tester',
          status: 'ASSIGNED',
          created_at: '2026-04-01T00:00:00Z',
          updated_at: '2026-04-01T00:00:00Z',
          // The write advances the event revision; the matrix refresh carries it too.
          event_revision: UPDATED_EVENT_REVISION,
        }),
      })
    })
    await page.route(/\/api\/v1\/districts\/district-1\/matrix(?:\?.*)?$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          assignmentCreated
            ? matrixResponse({
                isGap: false,
                leaderName: 'Pr. Tester',
                assignmentId: 'assignment-1',
                assignmentStatus: 'ASSIGNED',
                revision: UPDATED_EVENT_REVISION,
              })
            : matrixResponse({ isGap: true }),
        ),
      })
    })

    await page.goto(`${FRONTEND_URL}/matrix`)

    await expect(page.getByRole('button', { name: /LÜCKE/i })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: /LÜCKE/i }).click()

    const input = page.getByPlaceholder(/Name eingeben/i)
    await input.fill('Pr. Tester')
    await page.getByRole('button', { name: 'Zuweisen' }).click()

    await expect(page.getByRole('heading', { name: /Zuweisung bearbeiten/i })).toBeHidden({
      timeout: 10000,
    })

    // Verify the gap is gone and the assigned leader is visible
    await expect(page.getByRole('button', { name: /LÜCKE/i })).toBeHidden({ timeout: 10000 })
    await expect(page.getByRole('button', { name: /Pr\. Tester/ })).toBeVisible({ timeout: 10000 })

    // The create was conditional on the revision the matrix showed, exactly once.
    expect(ifMatchHeaders).toEqual([EVENT_REVISION])
  })
})
