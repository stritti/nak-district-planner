// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useDistrictsStore } from '../stores/districts'
import { useAuthStore } from '../stores/auth'
import PersonalCalendarView from './PersonalCalendarView.vue'
import CopyButton from '../components/CopyButton.vue'
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

it('provides an absolute subscription URL to the copy action', async () => {
  vi.mocked(api.createPersonalToken).mockResolvedValue({
    id: 'fresh', token: 'secret', label: 'Mein Kalender',
  })
  const wrapper = mount(PersonalCalendarView)
  await flushPromises()
  await wrapper.get('[data-testid="create-feed"]').trigger('click')
  await flushPromises()

  expect(wrapper.getComponent(CopyButton).props('value')).toBe(
    `${window.location.origin}/api/v1/export/secret/calendar.ics`,
  )
})

it('keeps the newly created secret when dates change and events fail to reload', async () => {
  vi.mocked(api.createPersonalToken).mockResolvedValue({
    id: 'fresh', token: 'secret', label: 'Mein Kalender',
  })
  const wrapper = mount(PersonalCalendarView)
  await flushPromises()
  await wrapper.get('[data-testid="create-feed"]').trigger('click')
  await flushPromises()
  vi.mocked(api.listPersonalEvents).mockRejectedValueOnce(new Error('Zeitraum nicht geladen'))

  await wrapper.findAll('input[type="date"]')[0]!.setValue('2026-11-01')
  await flushPromises()

  expect(wrapper.get('[role="alert"]').text()).toContain('Zeitraum nicht geladen')
  expect(wrapper.getComponent(CopyButton).props('value')).toContain('/export/secret/')
  expect(api.listPersonalTokens).toHaveBeenCalledOnce()
})

it('does not discard a creation response when only the dates change', async () => {
  let resolveCreation!: (token: api.PersonalToken) => void
  vi.mocked(api.createPersonalToken).mockReturnValueOnce(new Promise((resolve) => {
    resolveCreation = resolve
  }))
  const wrapper = mount(PersonalCalendarView)
  await flushPromises()
  await wrapper.get('[data-testid="create-feed"]').trigger('click')
  await wrapper.findAll('input[type="date"]')[0]!.setValue('2026-11-01')
  await flushPromises()
  resolveCreation({ id: 'fresh', token: 'secret', label: 'Mein Kalender' })
  await flushPromises()

  expect(wrapper.getComponent(CopyButton).props('value')).toContain('/export/secret/')
})

it('clears secrets on an identity switch even when event loading fails', async () => {
  vi.mocked(api.createPersonalToken).mockResolvedValue({
    id: 'fresh', token: 'private-secret', label: 'Mein Kalender',
  })
  const wrapper = mount(PersonalCalendarView)
  await flushPromises()
  await wrapper.get('[data-testid="create-feed"]').trigger('click')
  await flushPromises()
  vi.mocked(api.listPersonalEvents).mockRejectedValueOnce(new Error('Access denied'))
  useAuthStore().user = { sub: 'other', email: 'other@example.org', name: 'Other' }
  await flushPromises()

  expect(wrapper.findComponent(CopyButton).exists()).toBe(false)
  expect(wrapper.html()).not.toContain('private-secret')
  // The district store clears its selection on identity changes.
  useDistrictsStore().selectedDistrictId = 'd'
  await flushPromises()
  expect(api.listPersonalTokens).toHaveBeenLastCalledWith('d', 'other')
})

it('ignores an old identity token response and remains usable after clearing the scope', async () => {
  let resolveTokens!: (tokens: api.PersonalToken[]) => void
  vi.mocked(api.listPersonalTokens).mockReturnValueOnce(new Promise((resolve) => {
    resolveTokens = resolve
  }))
  const wrapper = mount(PersonalCalendarView)
  await flushPromises()
  useDistrictsStore().selectedDistrictId = ''
  await flushPromises()
  resolveTokens([{ id: 'old', token: 'private-secret', label: 'Old' }])
  await flushPromises()

  expect(wrapper.find('[role="status"]').exists()).toBe(false)
  expect(wrapper.html()).not.toContain('private-secret')
})


it('reports token-loading failures without exposing a calendar link', async () => {
  vi.mocked(api.listPersonalTokens).mockRejectedValueOnce('token lookup failed')

  const wrapper = mount(PersonalCalendarView)
  await flushPromises()

  expect(wrapper.get('[role="alert"]').text()).toContain('Kalender konnte nicht geladen werden')
  expect(wrapper.findComponent(CopyButton).exists()).toBe(false)

  vi.mocked(api.listPersonalTokens).mockRejectedValueOnce(new Error('Access denied'))
  useDistrictsStore().selectedDistrictId = 'another-district'
  await flushPromises()

  expect(wrapper.get('[role="alert"]').text()).toContain('Access denied')
  expect(wrapper.findComponent(CopyButton).exists()).toBe(false)
})

it('ignores events returned from an obsolete date range', async () => {
  let resolveOldEvents!: (events: api.PersonalEvent[]) => void
  vi.mocked(api.listPersonalEvents).mockReturnValueOnce(new Promise((resolve) => {
    resolveOldEvents = resolve
  }))

  const wrapper = mount(PersonalCalendarView)
  await flushPromises()

  vi.mocked(api.listPersonalEvents).mockResolvedValueOnce([{
    planning_slot_id: 'new-slot',
    uid: 'new@nak',
    title: 'Current appointment',
    start_at: '2026-11-01T10:00:00Z',
    end_at: '2026-11-01T11:00:00Z',
    status: 'CONFIRMED',
    duties: ['Organist'],
    congregation_id: null,
  }])
  await wrapper.findAll('input[type="date"]')[0]!.setValue('2026-11-01')
  await flushPromises()

  resolveOldEvents([{
    planning_slot_id: 'obsolete-slot',
    uid: 'obsolete@nak',
    title: 'Obsolete appointment',
    start_at: '2026-10-01T10:00:00Z',
    end_at: '2026-10-01T11:00:00Z',
    status: 'CONFIRMED',
    duties: [],
    congregation_id: null,
  }])
  await flushPromises()

  expect(wrapper.text()).toContain('Current appointment')
  expect(wrapper.text()).not.toContain('Obsolete appointment')
})

it('does not show errors from an obsolete event request', async () => {
  let rejectOldEvents!: (reason: unknown) => void
  vi.mocked(api.listPersonalEvents).mockReturnValueOnce(new Promise((_, reject) => {
    rejectOldEvents = reject
  }))

  const wrapper = mount(PersonalCalendarView)
  await flushPromises()

  await wrapper.findAll('input[type="date"]')[0]!.setValue('2026-11-01')
  await flushPromises()
  rejectOldEvents(new Error('Old request denied'))
  await flushPromises()

  expect(wrapper.text()).not.toContain('Old request denied')
  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  expect(wrapper.findAll('[data-testid="personal-event"]')).toHaveLength(1)
})

it('ignores a rejected token request after switching districts', async () => {
  let rejectOldTokens!: (reason: unknown) => void
  vi.mocked(api.listPersonalTokens).mockReturnValueOnce(new Promise((_, reject) => {
    rejectOldTokens = reject
  }))

  const wrapper = mount(PersonalCalendarView)
  await flushPromises()

  useDistrictsStore().selectedDistrictId = 'another-district'
  await flushPromises()
  rejectOldTokens(new Error('Old district denied'))
  await flushPromises()

  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  expect(wrapper.html()).not.toContain('Old district denied')
  expect(api.listPersonalTokens).toHaveBeenLastCalledWith('another-district', 'me')
})

it('discards a token created for a district that is no longer selected', async () => {
  let resolveCreation!: (token: api.PersonalToken) => void
  vi.mocked(api.createPersonalToken).mockReturnValueOnce(new Promise((resolve) => {
    resolveCreation = resolve
  }))

  const wrapper = mount(PersonalCalendarView)
  await flushPromises()
  await wrapper.get('[data-testid="create-feed"]').trigger('click')

  useDistrictsStore().selectedDistrictId = ''
  await flushPromises()
  resolveCreation({ id: 'old', token: 'obsolete-private-token', label: 'Old district' })
  await flushPromises()

  expect(wrapper.html()).not.toContain('obsolete-private-token')
  expect(wrapper.findComponent(CopyButton).exists()).toBe(false)
  expect(wrapper.find('[role="status"]').exists()).toBe(false)
})

it('ignores a late revocation failure after the district changes', async () => {
  let rejectRevocation!: (reason: unknown) => void
  vi.mocked(api.listPersonalTokens).mockResolvedValueOnce([{
    id: 'old', token: 'private-token', label: 'Old district',
  }])
  vi.mocked(api.revokePersonalToken).mockReturnValueOnce(new Promise((_, reject) => {
    rejectRevocation = reject
  }))

  const wrapper = mount(PersonalCalendarView)
  await flushPromises()
  await wrapper.get('button.btn-secondary').trigger('click')

  useDistrictsStore().selectedDistrictId = ''
  await flushPromises()
  rejectRevocation(new Error('Old district revocation failed'))
  await flushPromises()

  expect(wrapper.html()).not.toContain('private-token')
  expect(wrapper.html()).not.toContain('Old district revocation failed')
  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
})
