// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import type { EventResponse } from '../../../api/events'
import EventCreateModal, { type EventCreateForm } from '../EventCreateModal.vue'
import EventMonthGrid from '../EventMonthGrid.vue'
import EventWeekGrid from '../EventWeekGrid.vue'
import { eventPillClass, formatTime, regularEvents } from '../eventDisplay'

function event(overrides: Partial<EventResponse>): EventResponse {
  return {
    id: 'e1',
    title: 'Gottesdienst',
    category: 'Gottesdienst',
    status: 'ACTIVE',
    is_service: true,
    start_at: '2026-10-18T09:30:00',
    ...overrides,
  } as EventResponse
}

const day = { iso: '2026-10-18', day: 18, isToday: false, weekdayShort: 'So', currentMonth: true }

describe('eventDisplay', () => {
  it('formats times and hides midnight', () => {
    expect(formatTime('2026-10-18T09:05:00')).toBe('09:05')
    expect(formatTime('2026-10-18T00:00:00')).toBe('')
  })

  it('classifies pills by category, status and service flag', () => {
    expect(eventPillClass(event({ category: 'Feiertag' }))).toContain('amber')
    expect(eventPillClass(event({ status: 'CANCELLED' }))).toContain('line-through')
    expect(eventPillClass(event({}))).toContain('blue')
    expect(eventPillClass(event({ is_service: false }))).toContain('gray')
  })

  it('filters holidays out of regular events and tolerates undefined', () => {
    expect(regularEvents(undefined)).toEqual([])
    expect(regularEvents([event({}), event({ id: 'h', category: 'Feiertag' })])).toHaveLength(1)
  })
})

describe.each([
  ['week', EventWeekGrid],
  ['month', EventMonthGrid],
])('%s grid', (_name, Grid) => {
  const props = {
    days: [day],
    holidays: { '2026-10-18': ['Erntedank'] },
    eventsByDate: { '2026-10-18': [event({}), event({ id: 'h', category: 'Feiertag', title: 'Erntedank' })] },
    loading: false,
  }

  it('renders holidays and emits select for regular events only', async () => {
    const wrapper = mount(Grid, { props })
    expect(wrapper.text()).toContain('Erntedank')
    const pill = wrapper.findAll('div').find((el) => el.text().startsWith('Gottesdienst') && el.classes('cursor-pointer'))!
    await pill.trigger('click')
    expect(wrapper.emitted('select')?.[0][0]).toMatchObject({ id: 'e1' })
  })

  it('shows a loading state', () => {
    expect(mount(Grid, { props: { ...props, loading: true } }).text()).toContain('Laden')
  })
})

describe('EventMonthGrid overflow', () => {
  it('collapses more than three events', () => {
    const many = Array.from({ length: 5 }, (_, i) => event({ id: `e${i}`, title: `T${i}` }))
    const wrapper = mount(EventMonthGrid, {
      props: { days: [day], holidays: {}, eventsByDate: { '2026-10-18': many }, loading: false },
    })
    expect(wrapper.text()).toContain('+2 weitere')
  })
})

describe('EventCreateModal', () => {
  const form: EventCreateForm = {
    title: '', start: '', end: '', category: 'Gottesdienst', congregation_id: '', description: '', visibility: 'PUBLIC',
  }

  it('emits submit/close and shows errors', async () => {
    const wrapper = mount(EventCreateModal, { props: { form, congregations: [], error: 'Fehler', saving: false } })
    expect(wrapper.get('[role=alert]').text()).toBe('Fehler')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')).toHaveLength(1)
    await wrapper.get('button.btn-secondary').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})

describe('EventCreateModal close paths', () => {
  it('closes from backdrop, icon and cancel', async () => {
    const form: EventCreateForm = {
      title: '', start: '', end: '', category: '', congregation_id: '', description: '', visibility: 'PUBLIC',
    }
    const wrapper = mount(EventCreateModal, { props: { form, congregations: [{ id: 'c', name: 'G' }] as never[], error: '', saving: true } })
    await wrapper.get('.modal-backdrop').trigger('click')
    await wrapper.get('.modal-close').trigger('click')
    await wrapper.get('button.btn-secondary').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(3)
    expect(wrapper.get('button[type=submit]').attributes('disabled')).toBeDefined()
  })
})

describe('EventCreateModal form bindings', () => {
  it('writes every field back to the parent-owned form', async () => {
    const form: EventCreateForm = {
      title: '', start: '', end: '', category: '', congregation_id: '', description: '', visibility: 'PUBLIC',
    }
    const wrapper = mount(EventCreateModal, { props: { form, congregations: [{ id: 'c', name: 'G' }] as never[], error: '', saving: false } })
    await wrapper.get('#new-event-title').setValue('Titel')
    await wrapper.get('#new-event-start').setValue('2026-10-18T09:00')
    await wrapper.get('#new-event-end').setValue('2026-10-18T10:00')
    await wrapper.get('#new-event-category').setValue('Gottesdienst')
    await wrapper.get('#new-event-congregation').setValue('c')
    await wrapper.get('#new-event-description').setValue('Text')
    await wrapper.get('#new-event-visibility').setValue('INTERNAL')
    expect(form).toMatchObject({
      title: 'Titel', start: '2026-10-18T09:00', end: '2026-10-18T10:00', category: 'Gottesdienst',
      congregation_id: 'c', description: 'Text', visibility: 'INTERNAL',
    })
  })
})
