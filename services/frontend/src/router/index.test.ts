import { describe, expect, it } from 'vitest'
import ExternalCandidatesView from '../views/ExternalCandidatesView.vue'
import { router } from './index'

describe('external candidate admin route', () => {
  it('registers the authenticated review view at /admin/external-candidates', () => {
    const route = router.getRoutes().find((candidate) => candidate.name === 'admin-external-candidates')

    expect(route?.path).toBe('/admin/external-candidates')
    expect(route?.components?.default).toBe(ExternalCandidatesView)
    expect(route?.beforeEnter).toBeTruthy()
  })
})
