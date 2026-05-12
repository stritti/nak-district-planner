import { expect, test } from '@playwright/test'

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Matrix assignment flow', () => {
  test('gap can be assigned and turns into assigned cell', async ({ page }) => {
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
          memberships: [
            {
              role: 'PLANNER',
              scope_type: 'DISTRICT',
              scope_id: 'district-1',
            },
          ],
        }),
      )
    })

    let matrixCalls = 0

    await page.route('**/api/v1/districts', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ id: 'district-1', name: 'Bezirk 1' }]),
      })
    })

    await page.route('**/api/v1/districts/district-1/groups', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
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
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.route('**/api/v1/events/event-1/invitations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.route('**/api/v1/events/event-1/assignments', async (route) => {
      if (route.request().method() !== 'POST') {
        await route.fallback()
        return
      }
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
        }),
      })
    })

    await page.route('**/api/v1/districts/district-1/matrix**', async (route) => {
      matrixCalls += 1
      if (matrixCalls === 1) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
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
                    is_gap: true,
                    is_assignment_editable: true,
                    assignment_id: null,
                    assignment_status: null,
                    leader_id: null,
                    leader_name: null,
                  },
                },
              },
            ],
          }),
        })
        return
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
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
                  is_gap: false,
                  is_assignment_editable: true,
                  assignment_id: 'assignment-1',
                  assignment_status: 'ASSIGNED',
                  leader_id: null,
                  leader_name: 'Pr. Tester',
                },
              },
            },
          ],
        }),
      })
    })

    await page.goto(`${FRONTEND_URL}/matrix`)

    await expect(page.getByRole('button', { name: /Gottesdienst/i })).toBeVisible({ timeout: 10000 })
    await page.getByRole('button', { name: /Gottesdienst/i }).click()

    const input = page.getByPlaceholder(/Name eingeben/i)
    await input.fill('Pr. Tester')
    await page.getByRole('button', { name: 'Zuweisen' }).click()

    await expect(page.getByText('Pr. Tester')).toBeVisible({ timeout: 10000 })
  })
})
