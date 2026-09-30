import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ConflictBanner from '@/components/ConflictBanner.vue'
import type { ConflictItem } from '@/api/errors'

function conflict(severity: 'BLOCK' | 'WARN', ruleId: string, message: string): ConflictItem {
  return { rule_id: ruleId, severity, message, details: {} }
}

describe('ConflictBanner', () => {
  it('renders nothing when there are no conflicts', () => {
    const wrapper = mount(ConflictBanner, { props: { conflicts: [] } })
    expect(wrapper.find('[data-testid="conflict-banner"]').exists()).toBe(false)
  })

  it('shows blocking style and headline for BLOCK conflicts', () => {
    const wrapper = mount(ConflictBanner, {
      props: {
        conflicts: [conflict('BLOCK', 'no_double_booking', 'Bereits zugewiesen')],
      },
    })
    const banner = wrapper.find('[data-testid="conflict-banner"]')
    expect(banner.exists()).toBe(true)
    expect(banner.text()).toContain('Zuweisung blockiert')
    expect(banner.text()).toContain('Bereits zugewiesen')
    expect(wrapper.find('[data-testid="conflict-no_double_booking"]').exists()).toBe(true)
    expect(banner.classes().some((c) => c.includes('red'))).toBe(true)
  })

  it('shows warning style and headline for WARN-only conflicts', () => {
    const wrapper = mount(ConflictBanner, {
      props: {
        conflicts: [conflict('WARN', 'travel_time_check', 'Wechselzeit unterschritten')],
      },
    })
    const banner = wrapper.find('[data-testid="conflict-banner"]')
    expect(banner.text()).toContain('Konflikte vorhanden')
    expect(banner.classes().some((c) => c.includes('amber'))).toBe(true)
    expect(banner.classes().some((c) => c.includes('red'))).toBe(false)
  })

  it('treats mixed conflicts as blocking', () => {
    const wrapper = mount(ConflictBanner, {
      props: {
        conflicts: [
          conflict('WARN', 'travel_time_check', 'Wechselzeit'),
          conflict('BLOCK', 'leader_available', 'Abwesend'),
        ],
      },
    })
    expect(wrapper.find('[data-testid="conflict-banner"]').text()).toContain('Zuweisung blockiert')
  })
})
