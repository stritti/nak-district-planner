import { beforeEach, describe, expect, it } from 'vitest'
import type { NavigationGuard } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getRouterPinia, router } from './index'

function authGuard(): NavigationGuard {
  const route = router.getRoutes().find((candidate) => candidate.name === 'events')
  expect(route?.beforeEnter).toBeTruthy()
  return route!.beforeEnter as NavigationGuard
}

async function invokeGuard(): Promise<unknown> {
  const guard = authGuard()
  return await new Promise((resolve, reject) => {
    try {
      guard({} as never, {} as never, resolve as never)
    } catch (error) {
      reject(error)
    }
  })
}

describe('router', () => {
  beforeEach(() => {
    useAuthStore(getRouterPinia()).clearAuth()
  })

  it('registers the authenticated external candidate review route', () => {
    const route = router.getRoutes().find((candidate) => candidate.name === 'admin-external-candidates')
    const resolved = router.resolve('/admin/external-candidates')

    expect(route?.path).toBe('/admin/external-candidates')
    expect(route?.beforeEnter).toBeTruthy()
    expect(resolved.name).toBe('admin-external-candidates')
    expect(resolved.matched).toHaveLength(1)
  })

  it('reuses one standalone Pinia instance for router guards', () => {
    expect(getRouterPinia()).toBe(getRouterPinia())
  })

  it('redirects unauthenticated guarded navigation to login', async () => {
    await expect(invokeGuard()).resolves.toBe('/login')
  })

  it('allows authenticated guarded navigation', async () => {
    const auth = useAuthStore(getRouterPinia())
    auth.setToken(
      { accessToken: 'access', idToken: 'id', expiresAt: Math.floor(Date.now() / 1000) + 3600 },
      { sub: 'user' },
    )

    await expect(invokeGuard()).resolves.toBeUndefined()
  })

  it('loads the external-candidates view lazily', async () => {
    const route = router.getRoutes().find((candidate) => candidate.name === 'admin-external-candidates')
    const loader = route?.components?.default as (() => Promise<unknown>) | undefined

    expect(loader).toBeTypeOf('function')
    await expect(loader!()).resolves.toBeTruthy()
  })
})
