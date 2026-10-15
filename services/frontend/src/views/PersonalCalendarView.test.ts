// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useDistrictsStore } from '../stores/districts'
import { useAuthStore } from '../stores/auth'
import PersonalCalendarView from './PersonalCalendarView.vue'
import * as api from '../api/personalCalendar'
vi.mock('../api/personalCalendar', () => ({ listPersonalEvents: vi.fn(), listPersonalTokens: vi.fn(), createPersonalToken: vi.fn(), revokePersonalToken: vi.fn() }))
beforeEach(() => {
 setActivePinia(createPinia()); vi.clearAllMocks()
 useAuthStore().user = { sub: 'me', email: 'me@example.org', name: 'Me' }
 useDistrictsStore().selectedDistrictId = 'd'
 vi.mocked(api.listPersonalEvents).mockResolvedValue([{ planning_slot_id: 's', uid: 's@nak', title: 'GD', start_at: '2026-10-13T10:00:00Z', end_at: '2026-10-13T11:00:00Z', status: 'CANCELLED', duties: ['Organist', 'Dirigent'], congregation_id: 'c' }])
 vi.mocked(api.listPersonalTokens).mockResolvedValue([])
 vi.mocked(api.revokePersonalToken).mockResolvedValue(undefined)
})
it('renders one event with several duties and cancellation', async () => {
 const wrapper = mount(PersonalCalendarView); await flushPromises()
 expect(wrapper.findAll('[data-testid="personal-event"]')).toHaveLength(1)
 expect(wrapper.text()).toContain('Organist, Dirigent'); expect(wrapper.text()).toContain('Abgesagt')
})
it('renders the ICS link for a stored token with a secret', async () => {
  vi.mocked(api.listPersonalTokens).mockResolvedValue([
    { id: 't', token: 'fresh-secret', label: 'Mein Kalender' },
  ])
  const wrapper = mount(PersonalCalendarView)
  await flushPromises()
  expect(wrapper.get('a').attributes('href')).toContain('/api/v1/export/fresh-secret/calendar.ics')
})

it('hides the ICS link when the stored token has no reusable secret', async () => {
  vi.mocked(api.listPersonalTokens).mockResolvedValue([{ id: 't', label: 'Mein Kalender' }])
  const wrapper = mount(PersonalCalendarView)
  await flushPromises()
  expect(wrapper.find('a').exists()).toBe(false)
  expect(wrapper.text()).toContain('Secret nur direkt nach dem Erstellen sichtbar')
})

it('creates only an own subject-bound internal feed', async () => {
 vi.mocked(api.createPersonalToken).mockResolvedValue({ id: 't', token: 'secret', label: 'Mein Kalender' })
 const wrapper = mount(PersonalCalendarView); await flushPromises()
 await wrapper.get('[data-testid="create-feed"]').trigger('click'); await flushPromises()
 expect(api.createPersonalToken).toHaveBeenCalledWith('d', 'me')
 expect(wrapper.get('a').attributes('href')).toContain('/api/v1/export/secret/calendar.ics')
})
it('clears private results on district switch and reports denied access', async () => {
 const wrapper = mount(PersonalCalendarView); await flushPromises()
 vi.mocked(api.listPersonalEvents).mockRejectedValue(new Error('Access denied'))
 useDistrictsStore().selectedDistrictId = 'other'; await flushPromises()
 expect(wrapper.findAll('[data-testid="personal-event"]')).toHaveLength(0)
 expect(wrapper.get('[role="alert"]').text()).toContain('Access denied')
})
it('revokes feeds and reloads when the requested dates change', async () => {
 vi.mocked(api.listPersonalTokens).mockResolvedValue([{id:'t',token:'secret',label:'Mein Kalender'}])
 const wrapper=mount(PersonalCalendarView);await flushPromises()
 await wrapper.get('button.btn-secondary').trigger('click');await flushPromises()
 expect(api.revokePersonalToken).toHaveBeenCalledWith('t');expect(wrapper.find('a').exists()).toBe(false)
 const dates=wrapper.findAll('input[type="date"]')
 await dates[0]!.setValue('2026-11-01');await dates[1]!.setValue('2026-11-30');await flushPromises()
 expect(api.listPersonalEvents).toHaveBeenLastCalledWith('d','2026-11-01','2026-11-30')
})
it('reports feed creation and revocation failures without leaking stale state', async () => {
 vi.mocked(api.listPersonalTokens).mockResolvedValue([{id:'t',token:'secret',label:'Mein Kalender'}])
 const wrapper=mount(PersonalCalendarView);await flushPromises()
 vi.mocked(api.createPersonalToken).mockRejectedValueOnce('create')
 await wrapper.get('[data-testid="create-feed"]').trigger('click');await flushPromises()
 expect(wrapper.get('[role="alert"]').text()).toContain('Kalenderlink konnte nicht erstellt werden')
 vi.mocked(api.revokePersonalToken).mockRejectedValueOnce(new Error('Widerruf verweigert'))
 await wrapper.get('button.btn-secondary').trigger('click');await flushPromises()
 expect(wrapper.get('[role="alert"]').text()).toContain('Widerruf verweigert')
})
it('does not request private data without a selected district or identity', async () => {
 useDistrictsStore().selectedDistrictId='';useAuthStore().user=null
 const wrapper=mount(PersonalCalendarView);await flushPromises()
 expect(api.listPersonalEvents).not.toHaveBeenCalled();expect(api.listPersonalTokens).not.toHaveBeenCalled()
 expect(wrapper.text()).toContain('Bitte einen Bezirk auswählen')
})
it('uses the safe fallback for non-error load failures', async () => {
 vi.mocked(api.listPersonalEvents).mockRejectedValueOnce('denied')
 const wrapper=mount(PersonalCalendarView);await flushPromises()
 expect(wrapper.get('[role="alert"]').text()).toContain('Kalender konnte nicht geladen werden')
})
it('renders active appointments without a cancellation warning', async () => {
 vi.mocked(api.listPersonalEvents).mockResolvedValueOnce([{planning_slot_id:'s',uid:'active@nak',title:'Probe',start_at:'2026-10-14T18:00:00Z',end_at:'2026-10-14T19:00:00Z',status:'CONFIRMED',duties:['Dirigent'],congregation_id:null}])
 const wrapper=mount(PersonalCalendarView);await flushPromises()
 expect(wrapper.text()).toContain('Probe');expect(wrapper.text()).not.toContain('Abgesagt')
})
