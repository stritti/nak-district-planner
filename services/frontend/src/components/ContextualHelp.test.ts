import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import ContextualHelp from './ContextualHelp.vue'
import { useAuthStore } from '../stores/auth'
import { useHelpStore } from '../stores/help'

const RouterLinkStub = defineComponent({
  props: ['to'],
  setup(_, { slots }) { return () => h('a', slots.default?.()) },
})

beforeEach(() => {
  localStorage.clear()
  setActivePinia(createPinia())
})

function render(context: 'login' | 'events' | 'matrix' = 'login') {
  return mount(ContextualHelp, { props: { context }, global: { stubs: { RouterLink: RouterLinkStub } } })
}

describe('ContextualHelp', () => {
  it('discloses guidance without blocking login actions and restores hidden guidance', async () => {
    const wrapper = render()
    expect(wrapper.text()).toContain('Anmelden und Zugang erhalten')
    expect(wrapper.text()).not.toContain('Wähle „Mit Single Sign-on anmelden“')
    await wrapper.get('button[aria-expanded="false"]').trigger('click')
    expect(wrapper.text()).toContain('Wähle „Mit Single Sign-on anmelden“')
    await wrapper.get('button[aria-label="Anmelden und Zugang erhalten ausblenden"]').trigger('click')
    expect(wrapper.text()).not.toContain('Anmelden und Zugang erhalten')
    await wrapper.get('button').trigger('click')
    expect(wrapper.text()).toContain('Anmelden und Zugang erhalten')
  })

  it('does not expose planner guidance to viewer accounts', () => {
    const auth = useAuthStore()
    auth.setToken({ accessToken: 'test', idToken: 'test', expiresAt: Date.now() / 1000 + 60 }, { sub: 'viewer' })
    auth.accessStatus = 'ACTIVE'
    auth.memberships = [{ role: 'VIEWER', scope_type: 'DISTRICT', scope_id: 'd' }]
    expect(render('events').text()).toContain('Ereignisse finden')
    expect(render('matrix').find('[data-testid="contextual-help"]').exists()).toBe(false)
  })

  it('keeps guest preferences distinct from the logged-in identity', async () => {
    const guest = render()
    await guest.get('button[aria-label="Anmelden und Zugang erhalten ausblenden"]').trigger('click')
    guest.unmount()
    const auth = useAuthStore()
    auth.setToken({ accessToken: 'test', idToken: 'test', expiresAt: Date.now() / 1000 + 60 }, { sub: 'alice' })
    auth.accessStatus = 'ACTIVE'
    auth.memberships = [{ role: 'PLANNER', scope_type: 'DISTRICT', scope_id: 'd' }]
    const helpStore = useHelpStore()
    expect(helpStore.identity).toBe('user:alice')
    expect(helpStore.hidden).toEqual([])
    auth.clearAuth()
    expect(helpStore.hidden).toHaveLength(1)
  })
})