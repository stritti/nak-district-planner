import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useToastStore } from '../stores/toast'
import ToastContainer from './ToastContainer.vue'

function setup() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const store = useToastStore()
  const wrapper = mount(ToastContainer, {
    global: { plugins: [pinia] },
    attachTo: document.body,
  })
  return { store, wrapper }
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.runOnlyPendingTimers()
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('ToastContainer and toast store', () => {
  it('renders every semantic toast type with message, action and progress styling', async () => {
    const { store, wrapper } = setup()
    const actions = {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    }

    store.addToast({ type: 'success', title: 'Success', message: 'Done', duration: 1000, action: { label: 'Undo success', onClick: actions.success } })
    store.addToast({ type: 'error', title: 'Error', duration: 0, action: { label: 'Undo error', onClick: actions.error } })
    store.addToast({ type: 'warning', title: 'Warning', duration: 0, action: { label: 'Undo warning', onClick: actions.warning } })
    store.addToast({ type: 'info', title: 'Info', duration: 0, action: { label: 'Undo info', onClick: actions.info } })
    await wrapper.vm.$nextTick()

    const alerts = document.body.querySelectorAll('[role="alert"]')
    expect(alerts).toHaveLength(4)
    expect(document.body.textContent).toContain('✓')
    expect(document.body.textContent).toContain('✗')
    expect(document.body.textContent).toContain('!')
    expect(document.body.textContent).toContain('i')
    expect(document.body.textContent).toContain('Done')

    for (const [type, action] of Object.entries(actions)) {
      const actionButton = Array.from(document.body.querySelectorAll('button')).find(
        (button) => button.textContent?.includes(`Undo ${type}`),
      ) as HTMLButtonElement
      actionButton.click()
      expect(action).toHaveBeenCalledOnce()
    }

    expect(document.body.querySelector('.animate-progress')).not.toBeNull()
  })

  it('removes a toast from the close button and ignores unknown ids', async () => {
    const { store, wrapper } = setup()
    store.info('Information')
    await wrapper.vm.$nextTick()

    store.removeToast('missing')
    expect(store.messages).toHaveLength(1)

    const close = document.body.querySelector('button[aria-label="Schliessen"]') as HTMLButtonElement
    close.click()
    await wrapper.vm.$nextTick()
    expect(store.messages).toHaveLength(0)
  })

  it('applies convenience durations and automatically expires messages', async () => {
    const { store } = setup()

    store.success('success')
    store.error('error')
    store.warning('warning')
    store.info('info')

    expect(store.messages.map((message) => message.duration)).toEqual([5000, 8000, 6000, 5000])

    vi.advanceTimersByTime(5000)
    expect(store.messages.map((message) => message.type)).toEqual(['error', 'warning'])
    vi.advanceTimersByTime(3000)
    expect(store.messages).toHaveLength(0)
  })

  it('caps the visible queue at five messages', () => {
    const { store } = setup()

    for (let index = 1; index <= 6; index += 1) {
      store.addToast({ type: 'info', title: `toast-${index}`, duration: 0 })
    }

    expect(store.messages).toHaveLength(5)
    expect(store.messages[0].title).toBe('toast-2')
    expect(store.messages[4].title).toBe('toast-6')
  })
})
