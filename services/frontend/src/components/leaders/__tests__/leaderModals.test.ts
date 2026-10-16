// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ApproveRegistrationModal from '../ApproveRegistrationModal.vue'
import LeaderAddModal from '../LeaderAddModal.vue'
import LeaderEditModal from '../LeaderEditModal.vue'
import LeaderExportModal from '../LeaderExportModal.vue'
import RejectRegistrationModal from '../RejectRegistrationModal.vue'

const congregations = [{ id: 'c1', name: 'Gemeinde Eins' }] as never[]

const cases = [
  ['approve', ApproveRegistrationModal, { modal: { open: true, registrationId: 'r', name: 'Max', email: 'm@x.de', role: 'PLANNER', scope_type: 'DISTRICT', rank: null, congregation_id: null, special_role: null, error: 'Boom' }, congregations }, 'Genehmigen'],
  ['reject', RejectRegistrationModal, { modal: { open: true, registrationId: 'r', name: 'Max', reason: '', error: 'Boom' } }, 'Ablehnen'],
  ['add', LeaderAddModal, { modal: { open: true, congregationId: 'c1', name: 'Max', rank: 'Pr.', special_role: null, email: '', phone: '', error: 'Boom' }, congregationLabel: 'Gemeinde Eins' }, 'Hinzufügen'],
  ['edit', LeaderEditModal, { modal: { open: true, leaderId: 'l', revision: '1', name: 'Max', rank: 'Pr.', congregation_id: null, special_role: null, email: '', phone: '', notes: '', is_active: true, hidden_from_lists: false, service_end_date: '', error: 'Boom' }, congregations }, 'Speichern'],
  ['export', LeaderExportModal, { modal: { open: true, leaderId: 'l', leaderName: 'Max', leaderRank: 'Pr.', icsUrl: '', error: 'Boom' } }, 'Token erstellen'],
] as const

describe.each(cases)('%s modal', (_name, Component, props, submitLabel) => {
  const mountIt = () => mount(Component as never, { props: { ...props, saving: false } as never })

  it('shows the parent-owned error and emits submit', async () => {
    const wrapper = mountIt()
    expect(wrapper.text()).toContain('Boom')
    const submit = wrapper.findAll('button').find((b) => b.text().includes(submitLabel))!
    await submit.trigger('click')
    expect(wrapper.emitted('submit')).toHaveLength(1)
  })

  it('emits close from the backdrop, close icon and cancel button', async () => {
    const wrapper = mountIt()
    await wrapper.get('.modal-backdrop, .fixed').trigger('click')
    const buttons = wrapper.findAll('button')
    await buttons[0].trigger('click')
    await buttons.find((b) => b.text() === 'Abbrechen')!.trigger('click')
    expect(wrapper.emitted('close')?.length).toBe(3)
  })

  it('disables submit while saving', () => {
    const wrapper = mount(Component as never, { props: { ...props, saving: true } as never })
    const submit = wrapper.findAll('button').find((b) => b.text().includes(submitLabel) || b.text().includes('Speichern…'))!
    expect(submit.attributes('disabled')).toBeDefined()
  })
})

describe('export modal result state', () => {
  it('shows the calendar URL once a token exists', () => {
    const wrapper = mount(LeaderExportModal, {
      props: { saving: false, modal: { open: true, leaderId: 'l', leaderName: 'Max', leaderRank: '', icsUrl: 'https://x/calendar.ics', error: '' } },
    })
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('https://x/calendar.ics')
  })
})
