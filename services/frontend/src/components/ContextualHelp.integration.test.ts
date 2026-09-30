import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import ContextualHelp from './ContextualHelp.vue'
import { useAuthStore } from '../stores/auth'
import { useHelpStore } from '../stores/help'

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
})

function signIn(role: string) {
  const auth = useAuthStore()
  auth.setToken({ accessToken: 'test', idToken: 'test', expiresAt: Date.now() / 1000 + 60 }, { sub: role })
  auth.accessStatus = 'ACTIVE'
  auth.memberships = [{ role, scope_type: 'DISTRICT', scope_id: 'district' }]
}

function render(context: 'events' | 'matrix') {
  return mount(ContextualHelp, { props: { context }, global: { stubs: ['RouterLink'] } })
}

describe('contextual help role integration', () => {
  it('shows planner matrix help and restores it without affecting the events context', async () => {
    signIn('PLANNER')
    const store = useHelpStore()
    store.hide('planner-events', 'events')
    const wrapper = render('matrix')
    expect(wrapper.text()).toContain('Dienstplan-Matrix')
    await wrapper.get('button[aria-label="Mit der Dienstplan-Matrix arbeiten ausblenden"]').trigger('click')
    expect(wrapper.text()).not.toContain('Mit der Dienstplan-Matrix arbeiten')
    expect(wrapper.text()).toContain('Ausgeblendete Hilfe wiederherstellen')
    await wrapper.get('button').trigger('click')
    expect(wrapper.text()).toContain('Mit der Dienstplan-Matrix arbeiten')
    expect(store.isHidden('planner-events', 'events')).toBe(true)
  })

  it('shows nothing for an unknown authenticated role or pending access', () => {
    signIn('UNRELATED')
    expect(render('events').find('section').exists()).toBe(false)
    const auth = useAuthStore()
    auth.memberships = [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'district' }]
    auth.accessStatus = 'PENDING_APPROVAL'
    expect(render('matrix').find('section').exists()).toBe(false)
  })
})
