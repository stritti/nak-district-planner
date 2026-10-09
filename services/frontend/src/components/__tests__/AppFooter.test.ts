import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AppFooter from '@/components/AppFooter.vue'

describe('AppFooter', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows frontend and backend version without any sign-in', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ version: '1.0.0-rc.4' }))))

    const wrapper = mount(AppFooter)
    await flushPromises()

    expect(wrapper.get('[data-testid="app-footer"]').text()).toBe(
      'Frontend v0.0.0-test · Backend v1.0.0-rc.4',
    )
  })

  it('shows a dash for the backend while it is unknown or unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const wrapper = mount(AppFooter)
    await flushPromises()

    expect(wrapper.text()).toBe('Frontend v0.0.0-test · Backend –')
  })
})
