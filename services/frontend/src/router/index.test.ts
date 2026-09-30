import { describe, expect, it } from 'vitest'
import { router } from './index'

describe('external candidate admin route', () => {
  it('registers the authenticated review route at /admin/external-candidates', () => {
    const route = router.getRoutes().find((candidate) => candidate.name === 'admin-external-candidates')
    const resolved = router.resolve('/admin/external-candidates')

    expect(route?.path).toBe('/admin/external-candidates')
    expect(route?.beforeEnter).toBeTruthy()
    expect(resolved.name).toBe('admin-external-candidates')
    expect(resolved.matched).toHaveLength(1)
  })
})
