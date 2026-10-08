import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client')

import * as client from './client'
import { getAccessContext, getCurrentUser } from './auth'

const apiFetch = vi.mocked(client.apiFetch)

describe('auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({})
  })

  it('loads the current user', async () => {
    await getCurrentUser()
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/auth/me')
  })

  it('loads membership access context', async () => {
    await getAccessContext()
    expect(apiFetch).toHaveBeenLastCalledWith('/api/v1/auth/access')
  })
})
