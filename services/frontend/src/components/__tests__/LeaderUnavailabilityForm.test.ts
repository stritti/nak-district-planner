import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LeaderUnavailabilityForm from '@/components/LeaderUnavailabilityForm.vue'
import type { LeaderResponse } from '@/api/leaders'

const leaders: LeaderResponse[] = [
  {
    id: 'leader-1',
    name: 'Pastor Schmidt',
    district_id: 'district-1',
    rank: 'Pr.',
    congregation_id: null,
    special_role: null,
    user_sub: null,
    email: null,
    phone: null,
    notes: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00.000Z',
    updated_at: '2026-01-01T00:00:00.000Z',
  },
]

function mountForm(props: Partial<InstanceType<typeof LeaderUnavailabilityForm>['$props']> = {}) {
  return mount(LeaderUnavailabilityForm, {
    props: { leaders, ...props },
  })
}

describe('LeaderUnavailabilityForm', () => {
  it('clears an unavailable leader after a district switch', async () => {
    const wrapper = mountForm()
    await wrapper.setProps({ leaders: [] })
    await wrapper.find('form').trigger('submit')
    expect(wrapper.text()).toContain('Keine Amtsträger:innen vorhanden.')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('prevents duplicate submissions while saving', async () => {
    const wrapper = mountForm({ saving: true })
    await wrapper.find('form').trigger('submit')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('includes the entire last day and resets after saving', async () => {
    const wrapper = mountForm()
    await wrapper.find('[data-testid="unavailability-start-date"]').setValue('2026-05-01')
    await wrapper.find('[data-testid="unavailability-end-date"]').setValue('2026-05-01')
    await wrapper.find('[data-testid="unavailability-reason-select"]').setValue('URLAUB')
    await wrapper.find('form').trigger('submit')
    const payload = wrapper.emitted('submit')![0]![0] as { end_at: string; note: null }
    expect(payload.end_at).toBe('2026-05-01T21:59:59.999Z')
    expect(payload.note).toBeNull()
    wrapper.vm.reset()
    await wrapper.find('form').trigger('submit')
    expect(wrapper.text()).toContain('Bitte Beginn, Ende und Grund angeben.')
  })
  it('hides the leader select when only one leader is provided', () => {
    const wrapper = mountForm()
    expect(wrapper.find('[data-testid="unavailability-leader-select"]').exists()).toBe(false)
  })

  it('shows the leader select when multiple leaders are provided', () => {
    const wrapper = mountForm({
      leaders: [
        ...leaders,
        { ...leaders[0]!, id: 'leader-2', name: 'Priester Müller' },
      ],
    })
    expect(wrapper.find('[data-testid="unavailability-leader-select"]').exists()).toBe(true)
  })

  it('rejects a period where end is before start', async () => {
    const wrapper = mountForm()
    await wrapper.find('[data-testid="unavailability-start-date"]').setValue('2026-05-10')
    await wrapper.find('[data-testid="unavailability-end-date"]').setValue('2026-05-01')
    await wrapper.find('[data-testid="unavailability-reason-select"]').setValue('URLAUB')
    await wrapper.find('[data-testid="unavailability-submit"]').trigger('submit')
    expect(wrapper.find('[data-testid="unavailability-form-error"]').text()).toContain(
      'Das Ende muss nach dem Beginn liegen.',
    )
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('rejects submission when the reason is missing', async () => {
    const wrapper = mountForm()
    await wrapper.find('[data-testid="unavailability-start-date"]').setValue('2026-05-01')
    await wrapper.find('[data-testid="unavailability-end-date"]').setValue('2026-05-10')
    await wrapper.find('[data-testid="unavailability-submit"]').trigger('submit')
    expect(wrapper.find('[data-testid="unavailability-form-error"]').text()).toContain(
      'Bitte Beginn, Ende und Grund angeben.',
    )
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('emits a create payload for a valid period', async () => {
    const wrapper = mountForm()
    await wrapper.find('[data-testid="unavailability-start-date"]').setValue('2026-05-01')
    await wrapper.find('[data-testid="unavailability-end-date"]').setValue('2026-05-10')
    await wrapper.find('[data-testid="unavailability-reason-select"]').setValue('URLAUB')
    await wrapper
      .find('[data-testid="unavailability-note-input"]')
      .setValue('Familienurlaub')
    await wrapper.find('[data-testid="unavailability-submit"]').trigger('submit')
    const events = wrapper.emitted('submit')
    expect(events).toHaveLength(1)
    const payload = events![0]![0] as {
      leader_id: string
      start_at: string
      end_at: string
      reason: string
      note: string | null
    }
    expect(payload.leader_id).toBe('leader-1')
    expect(payload.reason).toBe('URLAUB')
    expect(payload.note).toBe('Familienurlaub')
    expect(payload.start_at).toBe('2026-04-30T22:00:00.000Z')
    expect(new Date(payload.end_at).getTime()).toBeGreaterThan(new Date(payload.start_at).getTime())
  })

  it('uses the preset leader id when provided', async () => {
    const wrapper = mountForm({ presetLeaderId: 'leader-1' })
    await wrapper.find('[data-testid="unavailability-start-date"]').setValue('2026-05-01')
    await wrapper.find('[data-testid="unavailability-end-date"]').setValue('2026-05-10')
    await wrapper.find('[data-testid="unavailability-reason-select"]').setValue('SPERRZEIT')
    await wrapper.find('[data-testid="unavailability-submit"]').trigger('submit')
    const events = wrapper.emitted('submit')
    expect((events![0]![0] as { leader_id: string }).leader_id).toBe('leader-1')
  })
})
