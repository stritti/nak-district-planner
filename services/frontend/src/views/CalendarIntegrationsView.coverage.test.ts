// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import * as calendarApi from '../api/calendarIntegrations'
import * as districtsApi from '../api/districts'
import { useDistrictsStore } from '../stores/districts'
import CalendarIntegrationsView from './CalendarIntegrationsView.vue'

vi.mock('../api/calendarIntegrations')
vi.mock('../api/districts')

function item(type: calendarApi.CalendarType, id = type): calendarApi.CalendarIntegrationResponse {
  return {
    id,
    district_id: 'd1',
    congregation_id: 'c1',
    name: `${type} Kalender`,
    type,
    sync_interval: 30,
    capabilities: ['READ'],
    is_active: true,
    last_synced_at: null,
    last_sync_error: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    default_category: null,
  }
}

function setup(items: calendarApi.CalendarIntegrationResponse[] = []) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const districts = useDistrictsStore()
  districts.districts = [{ id: 'd1', name: 'Bezirk Eins' }] as typeof districts.districts
  districts.selectedDistrictId = 'd1'
  vi.spyOn(districts, 'fetchDistricts').mockResolvedValue(undefined)
  vi.mocked(districtsApi.listCongregations).mockResolvedValue([
    { id: 'c1', name: 'Gemeinde Eins', district_id: 'd1' },
  ] as districtsApi.CongregationResponse[])
  vi.mocked(calendarApi.listIntegrations).mockResolvedValue({ items, total: items.length })

  return mount(CalendarIntegrationsView, { global: { plugins: [pinia] } })
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('CalendarIntegrationsView coverage gaps', () => {
  it('renders all provider badges and creates a CalDAV integration', async () => {
    vi.mocked(calendarApi.createIntegration).mockImplementation(async (payload) => ({
      ...item('CALDAV', 'created'),
      name: payload.name,
    }))
    const wrapper = setup([item('CALDAV'), item('GOOGLE'), item('MICROSOFT')])
    await flushPromises()

    expect(wrapper.text()).toContain('CALDAV Kalender')
    expect(wrapper.text()).toContain('GOOGLE Kalender')
    expect(wrapper.text()).toContain('MICROSOFT Kalender')

    const newButton = wrapper.findAll('button').find((button) => button.text().includes('Neue Integration'))!
    await newButton.trigger('click')
    await flushPromises()
    const modal = wrapper.findAll('.modal-panel').find((node) => node.text().includes('Neue Kalender-Integration'))!
    const selects = modal.findAll('select')
    await selects[0].setValue('d1')
    await selects.find((select) => select.findAll('option').some((option) => option.attributes('value') === 'CALDAV'))!.setValue('CALDAV')
    await flushPromises()
    await modal.get('input[placeholder="z. B. Gemeinde-Kalender Nord"]').setValue(' CalDAV Neu ')
    await modal.get('input[placeholder="https://caldav.example.com/calendar/"]').setValue(' https://cal.example.org/path ')
    const textInputs = modal.findAll('input[type="text"]')
    await textInputs[1].setValue(' alice ')
    await modal.get('input[type="password"]').setValue('secret')
    await modal.findAll('button').find((button) => button.text() === 'Anlegen')!.trigger('click')
    await flushPromises()

    expect(calendarApi.createIntegration).toHaveBeenCalledWith(expect.objectContaining({
      name: 'CalDAV Neu',
      type: 'CALDAV',
      credentials: {
        url: 'https://cal.example.org/path',
        username: 'alice',
        password: 'secret',
      },
    }))
  })

  it('edits CalDAV and JSON providers and surfaces update failures', async () => {
    vi.mocked(calendarApi.updateIntegration).mockResolvedValue(item('CALDAV'))
    const wrapper = setup([item('CALDAV'), item('GOOGLE', 'google')])
    await flushPromises()

    const editButtons = wrapper.findAll('button[title="Bearbeiten"]')
    await editButtons[0].trigger('click')
    let modal = wrapper.findAll('.modal-panel').find((node) => node.text().includes('Integration bearbeiten'))!
    await modal.get('input[type="url"]').setValue(' https://cal.example.org/new ')
    const caldavTextInputs = modal.findAll('input[type="text"]')
    await caldavTextInputs[1].setValue(' bob ')
    await modal.get('input[type="password"]').setValue('pw')
    await modal.findAll('button').find((button) => button.text() === 'Speichern')!.trigger('click')
    await flushPromises()
    expect(calendarApi.updateIntegration).toHaveBeenCalledWith('CALDAV', expect.objectContaining({
      credentials: { url: 'https://cal.example.org/new', username: 'bob', password: 'pw' },
    }))

    vi.mocked(calendarApi.updateIntegration).mockRejectedValueOnce(new Error('Update kaputt'))
    await wrapper.findAll('button[title="Bearbeiten"]')[1].trigger('click')
    modal = wrapper.findAll('.modal-panel').find((node) => node.text().includes('Integration bearbeiten'))!
    await modal.get('textarea').setValue('{"refresh_token":"r"}')
    await modal.findAll('button').find((button) => button.text() === 'Speichern')!.trigger('click')
    await flushPromises()
    expect(calendarApi.updateIntegration).toHaveBeenLastCalledWith('google', expect.objectContaining({
      credentials: { refresh_token: 'r' },
    }))
    expect(wrapper.text()).toContain('Update kaputt')

    await modal.get('textarea').setValue('{invalid')
    await modal.findAll('button').find((button) => button.text() === 'Speichern')!.trigger('click')
    await flushPromises()
    expect(calendarApi.updateIntegration).toHaveBeenLastCalledWith('google', expect.not.objectContaining({ credentials: expect.anything() }))
  })
})
