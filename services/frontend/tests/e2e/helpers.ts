// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { expect, type Page } from '@playwright/test'

export const FRONTEND_URL = 'http://localhost:5173'

export interface MatrixCellMock {
  event_id: string
  assignment_event_id: string
  assignment_id: string | null
  assignment_status: string | null
  is_gap: boolean
  leader_id: string | null
  leader_name: string | null
  event_title?: string
  category?: string
}

export interface MatrixResponseOptions {
  isGap: boolean
  leaderName?: string
  assignmentId?: string | null
  assignmentStatus?: string | null
}

export interface MockOIDCIdentity {
  sub: string
  email: string
  name: string
}

const DEFAULT_IDENTITY: MockOIDCIdentity = {
  sub: 'planner-user',
  email: 'planner@example.com',
  name: 'Planner User',
}

function jwt(claims: Record<string, unknown>): string {
  const payload = btoa(JSON.stringify(claims))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '')
  return `eyJhbGciOiJub25lIn0.${payload}.signature`
}

/**
 * Model an authenticated browser exactly like production: the SPA starts with
 * no persisted token and restores its memory-only identity from the backend's
 * HttpOnly refresh session.
 */
export async function mockAuthenticatedSession(
  page: Page,
  identity: MockOIDCIdentity = DEFAULT_IDENTITY,
): Promise<void> {
  await page.route('**/api/v1/auth/oidc/discovery', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      headers: { 'set-cookie': 'csrf_token=e2e-csrf; Path=/; SameSite=Strict' },
      body: JSON.stringify({
        authorization_endpoint: 'https://idp.example/authorize',
        token_endpoint: 'https://idp.example/token',
        userinfo_endpoint: 'https://idp.example/userinfo',
        client_id: 'planner-client',
      }),
    })
  })

  await page.route('**/api/v1/auth/oidc/token', async (route) => {
    expect(route.request().method()).toBe('POST')
    expect(route.request().postDataJSON()).toEqual({ grant_type: 'refresh_token' })
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'fake-access-token',
        id_token: jwt(identity),
        expires_in: 3600,
        refresh_session: true,
      }),
    })
  })
}

/**
 * Minimal matrix payload with a single congregation and a single cell
 * for the fixed date 2026-04-08.
 */
export function matrixResponse(options: MatrixResponseOptions) {
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
            assignment_id: options.assignmentId ?? null,
            assignment_status: options.assignmentStatus ?? null,
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

/**
 * Installs the standard planner session and matrix API route mocks.
 * Test-specific routes registered afterwards override these defaults.
 */
export async function setupAuthAndMatrix(
  page: Page,
  matrix: ReturnType<typeof matrixResponse>,
): Promise<void> {
  await page.addInitScript(() => {
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

  // Register auth restore routes last so they take precedence over the generic API mock.
  await mockAuthenticatedSession(page)
}
