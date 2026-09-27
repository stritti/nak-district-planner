import { expect, test } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

function matrixResponse(options: { isGap: boolean; leaderName?: string }) {
  return {
    dates: ['2026-04-08'],
    holidays: {},
    rows: [
      {
        congregation_id: 'cong-1',
        congregation_name: 'Gemeinde A',
        group_id: null,
        group_name: null,
        cells: {
          '2026-04-08': {
            event_id: 'event-1',
            assignment_event_id: 'event-1',
            invitation_count: 0,
            event_title: 'Gottesdienst',
            category: 'Gottesdienst',
            is_gap: options.isGap,
            is_assignment_editable: true,
            assignment_id: null,
            assignment_status: null,
            leader_id: null,
            leader_name: options.leaderName ?? null,
            has_deviation: false,
            planned_time: null,
            actual_start_at: null,
            deviation_start_diff_minutes: null,
            deviation_end_diff_minutes: null,
          },
        },
      },
    ],
  }
}

async function setupAuthAndMatrix(
  page: import('@playwright/test').Page,
  matrix: ReturnType<typeof matrixResponse>,
) {
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
          sub: 'planner-user',
          email: 'planner@example.com',
          name: 'Planner User',
        },
        isSuperadmin: false,
        accessStatus: 'ACTIVE',
        memberships: [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' }],
      }),
    )
    localStorage.setItem(
      'matrix',
      JSON.stringify({
        districtId: 'district-1',
        groupId: '',
        fromDt: '2026-04-01',
        toDt: '2026-04-30',
      }),
    )
    localStorage.setItem('districts', JSON.stringify({ selectedDistrictId: 'district-1' }))
  })

  await page.route('**/api/v1/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        sub: 'planner-user',
        email: 'planner@example.com',
        username: 'planner',
        name: 'Planner User',
        is_superadmin: false,
      }),
    })
  })
  await page.route('**/api/v1/auth/access', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ACTIVE',
        memberships: [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' }],
      }),
    })
  })
  await page.route('**/api/v1/districts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ id: 'district-1', name: 'Bezirk 1' }]),
    })
  })
  await page.route('**/api/v1/districts/district-1/groups', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
  await page.route('**/api/v1/districts/district-1/congregations**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'cong-1',
          name: 'Gemeinde A',
          district_id: 'district-1',
          group_id: null,
          group_name: null,
          invitation_target_type: null,
          invitation_target_congregation_id: null,
          invitation_external_note: null,
          service_times: [],
          created_at: '2026-04-01T00:00:00Z',
          updated_at: '2026-04-01T00:00:00Z',
        },
      ]),
    })
  })
  await page.route('**/api/v1/districts/district-1/leaders', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
  await page.route(/\/api\/v1\/events\/event-1\/invitations(?:\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  })
  await page.route(/\/api\/v1\/districts\/district-1\/matrix(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(matrix),
    })
  })
}

test.describe('Conflict handling in assignment flow', () => {
  test('BLOCK conflict (double booking) shows banner and disables submit', async ({ page }) => {
    await setupAuthAndMatrix(page, matrixResponse({ isGap: true }))
    let submitAttempts = 0
    await page.route(/\/api\/v1\/events\/event-1\/assignments(?:\?.*)?$/, async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback()
        return
      }
      submitAttempts++
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: {
            conflicts: [
              {
                rule_id: 'no_double_booking',
                severity: 'BLOCK',
                message: 'Amtsträger ist im Zeitraum bereits anderweitig zugewiesen.',
                details: {},
              },
            ],
          },
        }),
      })
    })

    await page.goto(`${FRONTEND_URL}/matrix`)
    await expect(page.getByRole('button', { name: /LÜCKE/i })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: /LÜCKE/i }).click()
    const input = page.getByPlaceholder(/Name eingeben/i)
    await input.fill('Pr. Konflikt')
    await page.getByRole('button', { name: 'Zuweisen' }).click()

    await expect(page.getByTestId('conflict-banner')).toBeVisible({ timeout: 10000 })
    await expect(page.getByTestId('conflict-no_double_booking')).toBeVisible()
    await expect(page.getByText('Zuweisung blockiert')).toBeVisible()

    const submit = page.getByTestId('submit-assignment')
    await expect(submit).toBeDisabled()
    await expect(submit).toHaveAttribute(
      'title',
      'Amtsträger ist im Zeitraum bereits anderweitig zugewiesen.',
    )
    expect(submitAttempts).toBe(1)
  })

  test('WARN conflict (travel time) requires explicit confirmation', async ({ page }) => {
    await setupAuthAndMatrix(page, matrixResponse({ isGap: true }))
    const bodies: string[] = []
    await page.route(/\/api\/v1\/events\/event-1\/assignments(?:\?.*)?$/, async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback()
        return
      }
      const body = route.request().postData() ?? ''
      bodies.push(body)
      if (body.includes('"confirm_warnings":true')) {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'assignment-1',
            event_id: 'event-1',
            leader_id: null,
            leader_name: 'Pr. Weitweg',
            status: 'ASSIGNED',
            created_at: '2026-04-01T00:00:00Z',
            updated_at: '2026-04-01T00:00:00Z',
          }),
        })
        return
      }
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: {
            conflicts: [
              {
                rule_id: 'travel_time_check',
                severity: 'WARN',
                message: 'Mindest-Wechselzeit von 30 Minuten wird unterschritten.',
                details: {},
              },
            ],
          },
        }),
      })
    })

    await page.goto(`${FRONTEND_URL}/matrix`)
    await expect(page.getByRole('button', { name: /LÜCKE/i })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: /LÜCKE/i }).click()
    const input = page.getByPlaceholder(/Name eingeben/i)
    await input.fill('Pr. Weitweg')
    await page.getByRole('button', { name: 'Zuweisen' }).click()

    await expect(page.getByTestId('conflict-banner')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Konflikte vorhanden')).toBeVisible()

    const confirmDialog = page.getByRole('dialog')
    await expect(confirmDialog).toBeVisible()
    await expect(page.getByText('Trotz Konflikt zuweisen?')).toBeVisible()
    await page.getByRole('button', { name: 'Trotzdem zuweisen' }).click()

    await expect(page.getByRole('dialog')).toBeHidden({ timeout: 10000 })
    expect(bodies.length).toBe(2)
    expect(bodies[1]).toContain('"confirm_warnings":true')
  })

  test('BLOCK conflict from leader unavailability cannot be overridden', async ({ page }) => {
    await setupAuthAndMatrix(page, matrixResponse({ isGap: true }))
    let submitAttempts = 0
    await page.route(/\/api\/v1\/events\/event-1\/assignments(?:\?.*)?$/, async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback()
        return
      }
      submitAttempts++
      await route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: {
            conflicts: [
              {
                rule_id: 'leader_available',
                severity: 'BLOCK',
                message: 'Amtsträger ist im Zeitraum abwesend.',
                details: {},
              },
            ],
          },
        }),
      })
    })

    await page.goto(`${FRONTEND_URL}/matrix`)
    await expect(page.getByRole('button', { name: /LÜCKE/i })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: /LÜCKE/i }).click()
    const input = page.getByPlaceholder(/Name eingeben/i)
    await input.fill('Pr. Urlauber')
    await page.getByRole('button', { name: 'Zuweisen' }).click()

    await expect(page.getByTestId('conflict-leader_available')).toBeVisible({ timeout: 10000 })
    const submit = page.getByTestId('submit-assignment')
    await expect(submit).toBeDisabled()
    expect(submitAttempts).toBe(1)
  })
})
