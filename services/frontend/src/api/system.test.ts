import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import { getVersion, triggerUpdate } from './system'

const apiFetch = vi.mocked(client.apiFetch)

describe('system API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
  })

  it('loads cached or refreshed version information', async () => {
    await getVersion()
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/system/version')

    await getVersion(true)
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/system/version?refresh=true')
  })

  it('triggers an update request', async () => {
    await triggerUpdate()
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/system/update', { method: 'POST' })
  })
})
