import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import type { CalendarIntegrationResponse, CalendarType, SyncResult } from '../api/calendarIntegrations'
import SyncStatusCard from './SyncStatusCard.vue'

const NOW = new Date('2026-10-05T12:00:00Z')

function integration(overrides: Partial<CalendarIntegrationResponse> = {}): CalendarIntegrationResponse {
  return {
    id: 'integration-1',
    name: 'Gemeindekalender',
    type: 'ICS',
    district_id: 'district-1',
    congregation_id: null,
    is_active: true,
    sync_interval: 60,
    capabilities: ['READ'],
    last_synced_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    default_category: null,
    ...overrides,
  } as CalendarIntegrationResponse
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW)
})

afterEach(() => vi.useRealTimers())

describe('SyncStatusCard', () => {
  it.each([
    ['ICS', 'bg-blue-100'],
    ['CALDAV', 'bg-purple-100'],
    ['GOOGLE', 'bg-red-100'],
    ['MICROSOFT', 'bg-sky-100'],
  ] as const)('renders the %s integration badge', (type: CalendarType, cssClass) => {
    const wrapper = mount(SyncStatusCard, {
      props: { integration: integration({ type }), isSyncing: false },
    })

    expect(wrapper.text()).toContain(type)
    expect(wrapper.find('.badge').classes()).toContain(cssClass)
  })

  it.each([
    [30_000, 'Gerade eben synchronisiert'],
    [15 * 60_000, 'Vor 15 Min. synchronisiert'],
    [3 * 60 * 60_000, 'Vor 3 Std. synchronisiert'],
    [2 * 24 * 60 * 60_000, 'Vor 2 Tagen synchronisiert'],
  ] as const)('formats the last sync age', (ageMs, label) => {
    const wrapper = mount(SyncStatusCard, {
      props: {
        integration: integration({ last_synced_at: new Date(NOW.getTime() - ageMs).toISOString() }),
        isSyncing: false,
      },
    })
    expect(wrapper.text()).toContain(label)
  })

  it('renders idle, syncing, error and inactive states with the correct button behavior', async () => {
    const wrapper = mount(SyncStatusCard, {
      props: { integration: integration(), isSyncing: false },
    })
    const button = wrapper.get('button')
    expect(button.attributes('disabled')).toBeUndefined()
    await button.trigger('click')
    expect(wrapper.emitted('sync')).toEqual([['integration-1']])

    await wrapper.setProps({ isSyncing: true })
    expect(wrapper.text()).toContain('Läuft…')
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    expect(wrapper.find('.animate-spin').exists()).toBe(true)

    await wrapper.setProps({ isSyncing: false, syncError: 'provider unavailable' })
    expect(wrapper.text()).toContain('provider unavailable')
    expect(wrapper.classes()).toContain('border-red-200')

    await wrapper.setProps({ syncError: null, integration: integration({ is_active: false }) })
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    expect(wrapper.get('button').attributes('title')).toBe('Integration ist inaktiv')
    expect(wrapper.classes()).toContain('opacity-60')
  })

  it('truncates long sync errors and renders sync results', () => {
    const longError = 'x'.repeat(130)
    const result: SyncResult = { created: 2, updated: 3, cancelled: 1, auto_matched: 4 } as SyncResult
    const wrapper = mount(SyncStatusCard, {
      props: {
        integration: integration(),
        isSyncing: false,
        syncError: longError,
        syncResult: result,
      },
    })

    expect(wrapper.text()).toContain(`${'x'.repeat(120)}…`)
    expect(wrapper.text()).not.toContain('x'.repeat(121))
    expect(wrapper.text()).toContain('+2 neu')
    expect(wrapper.text()).toContain('~3 aktualisiert')
    expect(wrapper.text()).toContain('✕1 abgesagt')
    expect(wrapper.text()).toContain('↔4 zugeordnet')
  })

  it('uses a green status after a successful sync and gray before the first sync', async () => {
    const wrapper = mount(SyncStatusCard, {
      props: { integration: integration(), isSyncing: false },
    })
    expect(wrapper.find('.bg-gray-400').exists()).toBe(true)

    await wrapper.setProps({
      integration: integration({ last_synced_at: new Date(NOW.getTime() - 60_000).toISOString() }),
    })
    expect(wrapper.find('.bg-green-500').exists()).toBe(true)
  })
})
