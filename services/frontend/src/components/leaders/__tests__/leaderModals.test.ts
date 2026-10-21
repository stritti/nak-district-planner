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
  ['add', LeaderAddModal, { modal: { open: true, congregationId: 'c1', name: 'Max', rank: 'Pr.', special_role: null, email: '', phone: '', error: 'Boom', duplicates: [] }, congregationLabel: 'Gemeinde Eins' }, 'Hinzufügen'],
  ['edit', LeaderEditModal, { modal: { open: true, leaderId: 'l', revision: '1', name: 'Max', rank: 'Pr.', assignments: [{ id: 'a1', congregation_id: 'c1', role: null, is_home: true, revision: 'r1' }], newAssignment: { target: '', role: null }, email: '', phone: '', notes: '', is_active: true, hidden_from_lists: false, service_end_date: '', error: 'Boom' }, congregations, canManage: () => true }, 'Speichern'],
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

describe('add modal duplicate hint', () => {
  const modal = (duplicates: { id: string; label: string }[]) => ({
    open: true, congregationId: null, name: 'Hans Müller', rank: 'Pr.', special_role: null,
    email: '', phone: '', error: '', duplicates,
  })

  it('shows no hint without matches and offers the normal action', () => {
    const wrapper = mount(LeaderAddModal as never, { props: { modal: modal([]), congregationLabel: '', saving: false } as never })
    expect(wrapper.find('[data-testid="duplicate-leader-hint"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Hinzufügen')
  })

  it('lists the matches, relabels the action and clears the hint when the name changes', async () => {
    const state = modal([{ id: 'l1', label: 'Hans Müller · Gemeinde Eins · aktiv' }])
    const wrapper = mount(LeaderAddModal as never, { props: { modal: state, congregationLabel: '', saving: false } as never })
    expect(wrapper.get('[data-testid="duplicate-leader-hint"]').text()).toContain('Gemeinde Eins')
    expect(wrapper.text()).toContain('Trotzdem neu anlegen')
    await wrapper.get('input[type="text"]').setValue('Hans Meier')
    expect(state.duplicates).toEqual([])
  })
})



describe('edit modal assignments', () => {
  const assignments = [
    { id: 'a1', congregation_id: 'c1', role: null, is_home: true, revision: 'r1' },
    { id: 'a2', congregation_id: 'c2', role: 'Gemeindevorsteher', is_home: false, revision: 'r2' },
    { id: 'a3', congregation_id: null, role: null, is_home: false, revision: 'r3' },
  ]
  const twoCongregations = [
    { id: 'c1', name: 'Gemeinde Eins' },
    { id: 'c2', name: 'Gemeinde Zwei' },
    { id: 'c3', name: 'Gemeinde Drei' },
  ] as never[]
  const mountAssignments = (canManage: (id: string | null) => boolean = () => true) =>
    mount(LeaderEditModal, {
      props: {
        saving: false,
        congregations: twoCongregations,
        canManage,
        modal: {
          open: true, leaderId: 'l', revision: '1', name: 'Max', rank: 'Pr.', assignments,
          newAssignment: { target: '', role: null }, email: '', phone: '', notes: '', is_active: true,
          hidden_from_lists: false, service_end_date: '', error: '',
        } as never,
      },
    })

  it('lists every assignment with the home marker', () => {
    const rows = mountAssignments().findAll('[data-testid^="assignment-"]')
    expect(rows.map((row) => row.text())).toEqual([
      expect.stringContaining('Gemeinde Eins'),
      expect.stringContaining('Gemeinde Zwei'),
      expect.stringContaining('Bezirksebene'),
    ])
    expect(rows[0].text()).toContain('Heimat')
    expect(rows[1].text()).not.toMatch(/Heimat(?! festlegen)/)
  })

  it('offers only roles that fit the level of the row', () => {
    const rows = mountAssignments().findAll('[data-testid^="assignment-"]')
    expect(rows[0].findAll('option').map((o) => o.text())).toEqual(['Keine', 'Gemeindevorsteher'])
    expect(rows[2].findAll('option').map((o) => o.text())).toEqual(['Keine', 'Bezirksvorsteher'])
  })

  it('emits role, home and remove with the assignment it concerns', async () => {
    const wrapper = mountAssignments()
    const row = wrapper.get('[data-testid="assignment-a2"]')
    await row.get('select').setValue('')
    await row.findAll('button').find((b) => b.text() === 'Als Heimat festlegen')!.trigger('click')
    await row.findAll('button').find((b) => b.text() === 'Entfernen')!.trigger('click')
    expect(wrapper.emitted('assignment-role')![0]).toEqual([assignments[1], null])
    expect(wrapper.emitted('assignment-home')![0]).toEqual([assignments[1]])
    expect(wrapper.emitted('assignment-remove')![0]).toEqual([assignments[1]])
  })

  it('does not offer to remove the home assignment', () => {
    const home = mountAssignments().get('[data-testid="assignment-a1"]')
    expect(home.findAll('button').map((b) => b.text())).toEqual([])
  })

  it('disables the controls of assignments the user may not manage', () => {
    const wrapper = mountAssignments((id) => id === 'c1')
    const foreign = wrapper.get('[data-testid="assignment-a2"]')
    expect(foreign.get('select').attributes('disabled')).toBeDefined()
    expect(foreign.findAll('button').every((b) => b.attributes('disabled') !== undefined)).toBe(true)
    expect(wrapper.get('[data-testid="assignment-a1"]').get('select').attributes('disabled')).toBeUndefined()
  })

  it('offers no picker while nothing unassigned remains that the user may manage', () => {
    // c3 is not manageable here; c1, c2 and the district level are already assigned.
    const wrapper = mountAssignments((id) => id !== 'c3')
    expect(wrapper.find('select[aria-label="Neue Zuordnung"]').exists()).toBe(false)
  })

  it('adds a manageable, still unassigned congregation', async () => {
    const wrapper = mount(LeaderEditModal, {
      props: {
        saving: false,
        congregations: twoCongregations,
        canManage: () => true,
        modal: {
          open: true, leaderId: 'l', revision: '1', name: 'Max', rank: 'Pr.', assignments: assignments.slice(0, 1),
          newAssignment: { target: '', role: null }, email: '', phone: '', notes: '', is_active: true,
          hidden_from_lists: false, service_end_date: '', error: '',
        } as never,
      },
    })
    const picker = wrapper.get('select[aria-label="Neue Zuordnung"]')
    expect(picker.findAll('option').map((o) => o.text())).toEqual([
      'Zuordnung hinzufügen…', 'Bezirksebene', 'Gemeinde Zwei', 'Gemeinde Drei',
    ])
    const add = wrapper.findAll('button').find((b) => b.text() === 'Hinzufügen')!
    expect(add.attributes('disabled')).toBeDefined()
    await picker.setValue('c2')
    expect(wrapper.get('select[aria-label="Beauftragung der neuen Zuordnung"]').findAll('option').map((o) => o.text()))
      .toEqual(['Keine', 'Gemeindevorsteher'])
    await add.trigger('click')
    expect(wrapper.emitted('assignment-add')).toHaveLength(1)
  })
})
