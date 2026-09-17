import { expect, test } from '@playwright/test'

test('warning conflict requires explicit confirmation', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('auth', JSON.stringify({ token: { accessToken: 'e2e', idToken: 'e2e', expiresAt: Math.floor(Date.now() / 1000) + 3600 }, user: { sub: 'planner', email: 'planner@example.com', name: 'Planner' }, isSuperadmin: false, accessStatus: 'ACTIVE', memberships: [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' }] }))
    localStorage.setItem('matrix', JSON.stringify({ districtId: 'district-1', groupId: '', fromDt: '2026-04-01', toDt: '2026-04-30' }))
    localStorage.setItem('districts', JSON.stringify({ selectedDistrictId: 'district-1' }))
  })

  await page.route('**/api/v1/**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.route('**/api/v1/auth/me', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ sub: 'planner', email: 'planner@example.com', username: 'planner', name: 'Planner', given_name: 'Planner', family_name: 'User', is_superadmin: false }) }))
  await page.route('**/api/v1/auth/access', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'ACTIVE', memberships: [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district-1' }] }) }))
  await page.route('**/api/v1/districts', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ id: 'district-1', name: 'Bezirk 1' }]) }))
  await page.route('**/api/v1/districts/district-1/groups', async route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))
  await page.route('**/api/v1/districts/district-1/congregations**', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ id: 'cong-1', name: 'Gemeinde A', district_id: 'district-1', group_id: null, group_name: null, invitation_target_type: null, invitation_target_congregation_id: null, invitation_external_note: null, service_times: [], created_at: '2026-04-01T00:00:00Z', updated_at: '2026-04-01T00:00:00Z' }]) }))
  await page.route('**/api/v1/districts/district-1/leaders', async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{ id: 'leader-1', name: 'Warn Leader', district_id: 'district-1', rank: 'Pr.', congregation_id: 'cong-1', special_role: null, user_sub: null, email: null, phone: null, notes: null, is_active: true, created_at: '2026-04-01T00:00:00Z', updated_at: '2026-04-01T00:00:00Z' }]) }))
  await page.route(/\/api\/v1\/events\/event-warn\/invitations(?:\?.*)?$/, async route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }))

  let confirmed = false
  await page.route(/\/api\/v1\/events\/event-warn\/assignments(?:\?.*)?$/, async route => {
    const request = route.request()
    if (request.method() !== 'POST') return route.fallback()
    const body = request.postDataJSON() as { confirm_warnings?: boolean }
    if (!body.confirm_warnings) {
      return route.fulfill({ status: 409, contentType: 'application/json', body: JSON.stringify({ detail: { conflicts: [{ rule_id: 'travel_time_check', severity: 'WARN', message: 'Die Wechselzeit ist zu kurz.', details: {} }] } }) })
    }
    confirmed = true
    return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ id: 'assignment-1', event_id: 'event-warn', leader_id: 'leader-1', leader_name: null, status: 'ASSIGNED', created_at: '2026-04-01T00:00:00Z', updated_at: '2026-04-01T00:00:00Z' }) })
  })
  await page.route(/\/api\/v1\/districts\/district-1\/matrix(?:\?.*)?$/, async route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ dates: ['2026-04-08'], holidays: {}, rows: [{ congregation_id: 'cong-1', congregation_name: 'Gemeinde A', group_id: null, group_name: null, cells: { '2026-04-08': { event_id: 'event-warn', assignment_event_id: 'event-warn', invitation_count: 0, event_title: 'Gottesdienst', category: 'Gottesdienst', is_gap: !confirmed, is_assignment_editable: true, assignment_id: confirmed ? 'assignment-1' : null, assignment_status: confirmed ? 'ASSIGNED' : null, leader_id: confirmed ? 'leader-1' : null, leader_name: confirmed ? 'Warn Leader' : null, has_deviation: false, planned_time: null, actual_start_at: null, deviation_start_diff_minutes: null, deviation_end_diff_minutes: null } } }] }) }))

  await page.goto('http://localhost:5173/matrix')
  await page.getByRole('button', { name: /LÜCKE/i }).click()
  await page.getByPlaceholder(/Name eingeben/i).fill('Warn Leader')
  await page.getByRole('option', { name: /Warn Leader/i }).click()
  await page.getByRole('button', { name: 'Zuweisen' }).click()
  await expect(page.getByRole('alert')).toContainText('Konflikt erkannt')
  await page.getByRole('button', { name: /Trotz Warnung speichern/i }).click()
  expect(confirmed).toBe(true)
})
