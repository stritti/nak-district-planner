import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import {
  approveRegistration,
  deleteRegistration,
  getPendingRegistrationsOverview,
  listCongregationsPublic,
  listDistrictsPublic,
  listRegistrations,
  rejectRegistration,
  submitRegistration,
} from './registrations'

const apiFetch = vi.mocked(client.apiFetch)
const fetchMock = vi.fn<typeof fetch>()

describe('registration API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
    vi.unstubAllGlobals()
  })

  it('loads the public district and congregation choices without auth-aware apiFetch', async () => {
    fetchMock
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: 'district-1', name: 'Tuttlingen' }]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }))
      .mockResolvedValueOnce(new Response(JSON.stringify([{ id: 'congregation-1', name: 'Stockach' }]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }))

    await expect(listDistrictsPublic()).resolves.toEqual([{ id: 'district-1', name: 'Tuttlingen' }])
    await expect(listCongregationsPublic('district-1')).resolves.toEqual([
      { id: 'congregation-1', name: 'Stockach' },
    ])

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/v1/public/districts', {
      headers: { 'Content-Type': 'application/json' },
    })
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/public/districts/district-1/congregations',
      { headers: { 'Content-Type': 'application/json' } },
    )
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('submits a public registration with JSON headers and body', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ id: 'registration-1' }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    }))
    const body = {
      name: 'Max Mustermann',
      email: 'max@example.org',
      congregation_id: 'congregation-1',
    }

    await submitRegistration('district-1', body)

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/districts/district-1/registrations', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    })
  })

  it('sends the CSRF cookie value as header, the backend rejects cookie-only requests', async () => {
    document.cookie = 'csrf_token=signed-token; path=/'
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ id: 'r1' }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    }))

    await submitRegistration('d1', { name: 'A', email: 'a@example.org' })

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/districts/d1/registrations')
    expect(init?.method).toBe('POST')
    expect((init?.headers as Record<string, string>)['X-CSRF-Token']).toBe('signed-token')
  })

  it('surfaces public API errors including an available response body', async () => {
    fetchMock.mockResolvedValue(new Response('duplicate email', {
      status: 409,
      statusText: 'Conflict',
    }))

    await expect(listDistrictsPublic()).rejects.toThrow('409 Conflict: duplicate email')
  })

  it('surfaces public API errors even when reading the response body fails', async () => {
    const response = {
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      text: vi.fn().mockRejectedValue(new Error('stream failed')),
    } as unknown as Response
    fetchMock.mockResolvedValue(response)

    await expect(listDistrictsPublic()).rejects.toThrow('503 Service Unavailable')
  })

  it.each([
    new Response(null, { status: 204 }),
    new Response('', { status: 200, headers: { 'content-length': '0' } }),
  ])('handles an empty public response without parsing JSON', async (response) => {
    fetchMock.mockResolvedValue(response)

    await expect(listDistrictsPublic()).resolves.toBeUndefined()
  })

  it('lists registrations with and without status filters', async () => {
    await listRegistrations('district-1')
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/districts/district-1/registrations')

    await listRegistrations('district-1', 'PENDING')
    expect(apiFetch).toHaveBeenLastCalledWith(
      '/api/v1/districts/district-1/registrations?status=PENDING',
    )
  })

  it('covers approval, rejection, deletion and pending overview', async () => {
    const approval = {
      role: 'PLANNER' as const,
      scope_type: 'DISTRICT' as const,
      scope_id: 'district-1',
      congregation_id: null,
    }
    await approveRegistration('district-1', 'registration-1', approval)
    expect(apiFetch).toHaveBeenLastCalledWith(
      '/api/v1/districts/district-1/registrations/registration-1/approve',
      { method: 'POST', body: JSON.stringify(approval) },
    )

    await rejectRegistration('district-1', 'registration-1')
    expect(apiFetch).toHaveBeenLastCalledWith(
      '/api/v1/districts/district-1/registrations/registration-1/reject',
      { method: 'POST', body: JSON.stringify({}) },
    )

    await rejectRegistration('district-1', 'registration-1', { reason: 'Unklar' })
    expect(apiFetch).toHaveBeenLastCalledWith(
      '/api/v1/districts/district-1/registrations/registration-1/reject',
      { method: 'POST', body: JSON.stringify({ reason: 'Unklar' }) },
    )

    await deleteRegistration('district-1', 'registration-1')
    expect(apiFetch).toHaveBeenLastCalledWith(
      '/api/v1/districts/district-1/registrations/registration-1',
      { method: 'DELETE' },
    )

    await getPendingRegistrationsOverview()
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/registrations/pending-overview')
  })
})
