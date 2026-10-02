import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as api from './eventHooks'
import { apiFetch } from './client'

vi.mock('./client', () => ({ apiFetch: vi.fn() }))

beforeEach(() => {
  vi.resetAllMocks()
})

const input: api.EventHookInput = {
  recipient_role: 'PLANNER',
  subject_template: 'Neu: {event_title}',
  body_template: 'Quelle: {source}',
  is_active: true,
}
const path = '/api/v1/districts/district%2Fa/event-hooks'

describe('event hook API', () => {
  it('lists hooks and event types of the (encoded) district', async () => {
    vi.mocked(apiFetch).mockResolvedValue([])
    await api.listEventHooks('district/a')
    await api.listEventTypes('district/a')
    expect(apiFetch).toHaveBeenNthCalledWith(1, path)
    expect(apiFetch).toHaveBeenNthCalledWith(2, `${path}/event-types`)
  })

  it('posts the complete create payload', async () => {
    const create = { ...input, event_type: 'EXTERNAL_EVENT_DETECTED' as const }
    await api.createEventHook('district/a', create)
    expect(apiFetch).toHaveBeenCalledWith(path, { method: 'POST', body: JSON.stringify(create) })
  })

  it('replaces mutable fields with PUT and deactivates with DELETE', async () => {
    await api.updateEventHook('district/a', 'hook 1', input)
    await api.deactivateEventHook('district/a', 'hook 1')
    expect(apiFetch).toHaveBeenNthCalledWith(1, `${path}/hook%201`, {
      method: 'PUT',
      body: JSON.stringify(input),
    })
    expect(apiFetch).toHaveBeenNthCalledWith(2, `${path}/hook%201`, { method: 'DELETE' })
  })
})
