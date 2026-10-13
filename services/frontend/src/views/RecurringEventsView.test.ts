// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { reactive } from 'vue'
import RecurringEventsView from './RecurringEventsView.vue'
import * as api from '../api/recurringEvents'

vi.mock('../api/recurringEvents', () => ({
  listRecurringTemplates: vi.fn(),
  listRecurringChecklist: vi.fn(),
  createRecurringTemplate: vi.fn(),
  updateRecurringTemplate: vi.fn(),
  acceptRecurringOccurrence: vi.fn(),
  skipRecurringOccurrence: vi.fn(),
  reopenRecurringOccurrence: vi.fn(),
  resolveRecurringOccurrence: vi.fn(),
  bulkAcceptRecurringOccurrences: vi.fn(),
}))

const districtStore = reactive({
  selectedDistrictId: 'district-1',
  congregations: [
    { id: 'congregation-1', name: 'Gemeinde A' },
    { id: 'congregation-2', name: 'Gemeinde B' },
  ],
  fetchCongregations: vi.fn().mockResolvedValue(undefined),
})
const authStore = reactive({
  isSuperadmin: false,
  memberships: [
    { role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'district-1' },
  ],
})
vi.mock('../stores/districts', () => ({ useDistrictsStore: () => districtStore }))
vi.mock('../stores/auth', () => ({ useAuthStore: () => authStore }))

const template: api.RecurringTemplate = {
  id: 'template-1',
  district_id: 'district-1',
  congregation_id: 'congregation-1',
  title: 'Chorprobe',
  description: 'Gemeindechor',
  category: 'Musik',
  start_time: '19:30:00',
  duration_minutes: 90,
  recurrence: {
    kind: 'WEEKLY', weekdays: [2], anchor_date: '2026-11-03', interval: 1,
    day_of_month: null, weekday: null, ordinal: null, version: 1,
  },
  applicability: [],
  excluded_dates: ['2026-11-24'],
  active_from: null, active_until: null,
  is_active: true, revision: 4, timezone: 'Europe/Berlin',
}

const openOccurrence: api.ChecklistItem = {
  template_id: template.id,
  district_id: template.district_id,
  congregation_id: template.congregation_id,
  title: template.title,
  description: template.description,
  category: template.category,
  occurrence_local_date: '2026-11-03',
  start_time: template.start_time,
  duration_minutes: template.duration_minutes,
  template_revision: template.revision,
  status: 'OPEN',
  decision_status: null,
  planning_slot_id: null,
  reason: null,
}

function page(items: api.ChecklistItem[], total = items.length): api.ChecklistPage {
  return {
    items, total, limit: 50, offset: 0,
    counts: {
      OPEN: items.filter(item => item.status === 'OPEN').length,
      ACCEPTED: items.filter(item => item.status === 'ACCEPTED').length,
      SKIPPED: items.filter(item => item.status === 'SKIPPED').length,
      CONFLICT: items.filter(item => item.status === 'CONFLICT').length,
      NEEDS_REVIEW: items.filter(item => item.status === 'NEEDS_REVIEW').length,
    },
  }
}
let wrapper: VueWrapper | null = null

async function render(items: api.ChecklistItem[] = [openOccurrence], total?: number) {
  vi.mocked(api.listRecurringChecklist).mockResolvedValue(page(items, total))
  wrapper = mount(RecurringEventsView)
  await flushPromises()
  return wrapper
}

async function click(text: string): Promise<void> {
  const button = wrapper!.findAll('button').find(item => item.text().includes(text))
  if (!button) throw new Error(`Missing button ${text}`)
  await button.trigger('click')
  await flushPromises()
}

async function templatesTab(): Promise<void> {
  await click('Vorlagen')
}

beforeEach(() => {
  vi.resetAllMocks()
  districtStore.selectedDistrictId = 'district-1'
  districtStore.fetchCongregations = vi.fn().mockResolvedValue(undefined)
  authStore.isSuperadmin = false
  authStore.memberships = [{ role: 'DISTRICT_ADMIN', scope_type: 'DISTRICT', scope_id: 'district-1' }]
  vi.mocked(api.listRecurringTemplates).mockResolvedValue({ items: [template], total: 1 })
  vi.mocked(api.listRecurringChecklist).mockResolvedValue(page([openOccurrence]))
  vi.mocked(api.acceptRecurringOccurrence).mockResolvedValue({
    template_id: template.id,
    occurrence_local_date: openOccurrence.occurrence_local_date,
    status: 'ACCEPTED', planning_slot_id: 'slot-1',
  })
  vi.mocked(api.skipRecurringOccurrence).mockResolvedValue({
    template_id: template.id, occurrence_local_date: openOccurrence.occurrence_local_date,
    status: 'SKIPPED', planning_slot_id: null,
  })
  vi.mocked(api.reopenRecurringOccurrence).mockResolvedValue({
    template_id: template.id, occurrence_local_date: openOccurrence.occurrence_local_date,
    status: 'OPEN', planning_slot_id: null,
  })
  vi.mocked(api.resolveRecurringOccurrence).mockResolvedValue({
    template_id: template.id, occurrence_local_date: openOccurrence.occurrence_local_date,
    status: 'SKIPPED', planning_slot_id: null,
  })
  vi.mocked(api.bulkAcceptRecurringOccurrences).mockResolvedValue({
    results: [{
      template_id: template.id, occurrence_local_date: openOccurrence.occurrence_local_date,
      status: 'ACCEPTED', planning_slot_id: 'slot-1', error: null,
    }],
  })
  vi.mocked(api.createRecurringTemplate).mockResolvedValue(template)
  vi.mocked(api.updateRecurringTemplate).mockResolvedValue(template)
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = null
})

describe('recurring monthly checklist', () => {
  it('only loads proposals, without creating planning slots on opening', async () => {
    const view = await render()
    expect(view.text()).toContain('Chorprobe')
    expect(view.text()).toContain('1 Vorschläge')
    expect(api.listRecurringTemplates).toHaveBeenCalledWith('district-1', 50, 0)
    expect(api.createRecurringTemplate).not.toHaveBeenCalled()
    expect(api.acceptRecurringOccurrence).not.toHaveBeenCalled()
  })

  it('uses input styling for typed search and template fields', async () => {
    const view = await render()
    expect(view.get('#recurring-search').classes()).toContain('form-input')
    expect(view.get('#recurring-category').classes()).toContain('form-input')
    await templatesTab()
    await click('Vorlage anlegen')
    expect(view.get('[data-testid="recurring-template-form"] input[maxlength="500"]').classes())
      .toContain('form-input')
  })

  it('uses server-side search, category, organization and status filters', async () => {
    const view = await render()
    await view.get('#recurring-search').setValue('Chor')
    await view.get('#recurring-category').setValue('Musik')
    await view.get('#recurring-status').setValue('SKIPPED')
    await view.get('#recurring-congregation').setValue('congregation-1')
    await view.get('[data-testid="apply-recurring-filters"]').trigger('click')
    await flushPromises()
    expect(api.listRecurringChecklist).toHaveBeenLastCalledWith(
      'district-1',
      expect.objectContaining({
        q: 'Chor', category: 'Musik', status: 'SKIPPED',
        congregation_id: 'congregation-1', offset: 0,
      }),
    )
  })

  it('changes months and paginates after filter application', async () => {
    const view = await render([openOccurrence], 51)
    await view.get('button[aria-label="Nächster Monat"]').trigger('click')
    await flushPromises()
    const [, filters] = vi.mocked(api.listRecurringChecklist).mock.lastCall!
    expect(filters.month).toBeGreaterThan(0)
    await click('Weiter')
    expect(api.listRecurringChecklist).toHaveBeenLastCalledWith(
      'district-1', expect.objectContaining({ offset: 50 }),
    )
    await click('Zurück')
    expect(api.listRecurringChecklist).toHaveBeenLastCalledWith(
      'district-1', expect.objectContaining({ offset: 0 }),
    )
  })

  it('accepts selected occurrences only on explicit bulk confirmation', async () => {
    const view = await render()
    await view.get('input[type="checkbox"][aria-label="Chorprobe auswählen"]').setValue(true)
    expect(api.bulkAcceptRecurringOccurrences).not.toHaveBeenCalled()
    await view.get('[data-testid="bulk-accept"]').trigger('click')
    await flushPromises()
    expect(api.bulkAcceptRecurringOccurrences).toHaveBeenCalledWith(
      'district-1', [{
        template_id: template.id, occurrence_local_date: '2026-11-03', template_revision: 4,
      }],
    )
  })

  it('keeps unresolved bulk errors visible without inventing successful statuses', async () => {
    const view = await render()
    vi.mocked(api.bulkAcceptRecurringOccurrences).mockResolvedValueOnce({
      results: [{
        template_id: template.id, occurrence_local_date: '2026-11-03',
        status: null, planning_slot_id: null, error: 'STALE_TEMPLATE',
      }],
    })
    await view.get('input[type="checkbox"][aria-label="Chorprobe auswählen"]').setValue(true)
    await click('ausgewählte übernehmen')
    expect(view.get('[role="alert"]').text()).toContain('Vorlage wurde inzwischen geändert')
    expect(view.text()).toContain('Offen')
  })

  it('shows a safe localized message for unexpected invalid input errors', async () => {
    const view = await render()
    vi.mocked(api.bulkAcceptRecurringOccurrences).mockResolvedValueOnce({
      results: [{
        template_id: template.id, occurrence_local_date: '2026-11-03',
        status: null, planning_slot_id: null, error: 'INVALID_INPUT',
      }],
    })
    await view.get('input[type="checkbox"][aria-label="Chorprobe auswählen"]').setValue(true)
    await click('ausgewählte übernehmen')
    expect(view.get('[role="alert"]').text()).toContain('Ungültige Eingabe')
    expect(view.get('[role="alert"]').text()).not.toContain('INVALID_INPUT')
  })

  it('paginates large template lists without loading every template at once', async () => {
    vi.mocked(api.listRecurringTemplates).mockResolvedValue({
      items: [template], total: 51,
    })
    const view = await render()
    await templatesTab()
    expect(view.text()).toContain('51 Vorlagen')
    await view.get('[data-testid="next-template-page"]').trigger('click')
    await flushPromises()
    expect(api.listRecurringTemplates).toHaveBeenLastCalledWith('district-1', 50, 50)
    await view.get('[data-testid="previous-template-page"]').trigger('click')
    await flushPromises()
    expect(api.listRecurringTemplates).toHaveBeenLastCalledWith('district-1', 50, 0)
  })

  it('opens preview, sends edited concrete data, and closes after success', async () => {
    const view = await render()
    await click('Prüfen und übernehmen')
    const preview = view.get('[data-testid="recurring-preview"]')
    expect(preview.text()).toContain('PLANNED')
    const inputs = preview.findAll('input')
    await inputs[0].setValue('Andere Probe')
    await inputs[1].setValue('2026-11-04')
    await inputs[2].setValue('18:45')
    await inputs[3].setValue('75')
    await preview.find('textarea').setValue('Einzelfall')
    await click('Als Entwurf übernehmen')
    expect(api.acceptRecurringOccurrence).toHaveBeenCalledWith(
      'district-1',
      expect.objectContaining({
        template_revision: 4, title_override: 'Andere Probe',
        local_date_override: '2026-11-04', local_time_override: '18:45',
        duration_minutes_override: 75, description_override: 'Einzelfall',
      }),
    )
    expect(view.find('[data-testid="recurring-preview"]').exists()).toBe(false)
  })

  it('preserves preview and selection after backend conflict', async () => {
    const view = await render()
    vi.mocked(api.acceptRecurringOccurrence).mockRejectedValueOnce(new Error('409'))
    await click('Prüfen und übernehmen')
    await click('Als Entwurf übernehmen')
    expect(view.find('[data-testid="recurring-preview"]').exists()).toBe(true)
    expect(view.get('[role="alert"]').text()).toContain('409')
    await click('Abbrechen')
    expect(view.find('[data-testid="recurring-preview"]').exists()).toBe(false)
  })

  it('supports skip and explicit reopen actions', async () => {
    await render()
    await click('Auslassen')
    expect(api.skipRecurringOccurrence).toHaveBeenCalledWith(
      'district-1',
      expect.objectContaining({ template_revision: 4 }),
    )
    const skipped = { ...openOccurrence, status: 'SKIPPED' as const, decision_status: 'SKIPPED' as const }
    vi.mocked(api.listRecurringChecklist).mockResolvedValue(page([skipped]))
    await click('Filtern')
    await click('Wieder öffnen')
    expect(api.reopenRecurringOccurrence).toHaveBeenCalledWith(
      'district-1', expect.objectContaining({ template_id: template.id }),
    )
  })

  it('requires explicit resolution for accepted decisions with deleted slots', async () => {
    const missing = {
      ...openOccurrence, status: 'NEEDS_REVIEW' as const,
      decision_status: 'ACCEPTED' as const, reason: 'Termin gelöscht',
    }
    const view = await render([missing])
    await click('Als ausgelassen markieren')
    expect(api.resolveRecurringOccurrence).toHaveBeenCalledWith(
      'district-1', expect.objectContaining({ action: 'MARK_SKIPPED' }),
    )
    vi.mocked(api.listRecurringChecklist).mockResolvedValue(page([missing]))
    await click('Filtern')
    await click('Neu öffnen')
    expect(api.resolveRecurringOccurrence).toHaveBeenCalledWith(
      'district-1', expect.objectContaining({ action: 'REOPEN' }),
    )
    vi.mocked(api.listRecurringChecklist).mockResolvedValue(page([missing]))
    await click('Filtern')
    await view.get('input[aria-label="Slot-ID zur Zuordnung"]').setValue('slot-uuid')
    await click('Slot zuordnen')
    expect(api.resolveRecurringOccurrence).toHaveBeenCalledWith(
      'district-1', expect.objectContaining({ action: 'LINK_EXISTING', planning_slot_id: 'slot-uuid' }),
    )
  })

  it('marks DST ambiguity for manual preview instead of resolving a non-existing decision', async () => {
    await render([{
      ...openOccurrence, status: 'NEEDS_REVIEW', decision_status: null,
      reason: 'Lokale Uhrzeit benötigt eine manuelle Prüfung.',
    }])
    await click('Prüfen und übernehmen')
    expect(wrapper!.text()).toContain('Sommerzeit-Überlappung')
    const select = wrapper!.get('[data-testid="recurring-preview"] select')
    await select.setValue('1')
    await click('Als Entwurf übernehmen')
    expect(api.acceptRecurringOccurrence).toHaveBeenCalledWith(
      'district-1', expect.objectContaining({ fold: 1 }),
    )
  })

  it('does not expose write actions to viewers', async () => {
    authStore.memberships = [
      { role: 'VIEWER', scope_type: 'CONGREGATION', scope_id: 'congregation-1' },
    ]
    const view = await render()
    expect(view.find('[data-testid="bulk-accept"]').exists()).toBe(false)
    expect(view.text()).not.toContain('Prüfen und übernehmen')
    await templatesTab()
    expect(view.find('[data-testid="create-template"]').exists()).toBe(false)
    expect(view.text()).not.toContain('Deaktivieren')
  })

  it('allows congregation administrators to manage only their community', async () => {
    authStore.memberships = [
      { role: 'CONGREGATION_ADMIN', scope_type: 'CONGREGATION', scope_id: 'congregation-1' },
    ]
    const view = await render([
      openOccurrence,
      { ...openOccurrence, template_id: 'another', congregation_id: 'congregation-2' },
    ])
    expect(view.findAll('button').filter(btn => btn.text().includes('Prüfen und übernehmen'))).toHaveLength(1)
    await templatesTab()
    await click('Vorlage anlegen')
    expect(view.get('[data-testid="recurring-template-form"]').exists()).toBe(true)
  })

  it('clears old tenant results when switching districts', async () => {
    await render()
    districtStore.selectedDistrictId = ''
    await flushPromises()
    expect(wrapper!.text()).toContain('Wähle einen Bezirk')
    expect(wrapper!.text()).not.toContain('Chorprobe')
    districtStore.selectedDistrictId = 'district-2'
    await flushPromises()
    expect(api.listRecurringTemplates).toHaveBeenCalledWith('district-2', 50, 0)
  })
})

describe('recurring template editor', () => {
  it('creates a weekly template with a valid rule and explicit defaults', async () => {
    const view = await render()
    await templatesTab()
    await click('Vorlage anlegen')
    const form = view.get('[data-testid="recurring-template-form"]')
    await form.get('input[maxlength="500"]').setValue('Chor')
    await form.trigger('submit')
    await flushPromises()
    expect(api.createRecurringTemplate).toHaveBeenCalledWith(
      'district-1',
      expect.objectContaining({
        title: 'Chor', recurrence: expect.objectContaining({ kind: 'WEEKLY', weekdays: [2] }),
      }),
    )
    expect(view.find('[data-testid="recurring-template-form"]').exists()).toBe(false)
  })

  it('edits a saved template by revision without allowing a scope change', async () => {
    const view = await render()
    await templatesTab()
    await click('Bearbeiten')
    const form = view.get('[data-testid="recurring-template-form"]')
    await form.get('input[maxlength="500"]').setValue('Neue Chorprobe')
    await form.trigger('submit')
    await flushPromises()
    const patch = vi.mocked(api.updateRecurringTemplate).mock.lastCall![2]
    expect(patch.expected_revision).toBe(4)
    expect(patch.title).toBe('Neue Chorprobe')
    expect(patch).not.toHaveProperty('congregation_id')
  })

  it('deactivates an existing template with optimistic revision', async () => {
    await render()
    await templatesTab()
    await click('Deaktivieren')
    expect(api.updateRecurringTemplate).toHaveBeenCalledWith(
      'district-1', 'template-1', { is_active: false, expected_revision: 4 },
    )
  })

  it('normalizes monthly-day form and clears weekly-only fields', async () => {
    const view = await render()
    await templatesTab()
    await click('Vorlage anlegen')
    const form = view.get('[data-testid="recurring-template-form"]')
    const selects = form.findAll('select')
    await selects[1].setValue('MONTHLY_DAY')
    await form.get('input[type="number"][max="31"]').setValue('31')
    await form.get('input[maxlength="500"]').setValue('Monatsabend')
    await form.trigger('submit')
    await flushPromises()
    expect(api.createRecurringTemplate).toHaveBeenCalledWith(
      'district-1', expect.objectContaining({
        recurrence: expect.objectContaining({ kind: 'MONTHLY_DAY', day_of_month: 31, weekdays: [] }),
      }),
    )
  })

  it('normalizes last-weekday recurrence with dedicated weekday and ordinal', async () => {
    const view = await render()
    await templatesTab()
    await click('Vorlage anlegen')
    const form = view.get('[data-testid="recurring-template-form"]')
    await form.findAll('select')[1].setValue('MONTHLY_WEEKDAY')
    await form.get('input[maxlength="500"]').setValue('Senioren')
    await form.trigger('submit')
    await flushPromises()
    expect(api.createRecurringTemplate).toHaveBeenCalledWith(
      'district-1', expect.objectContaining({
        recurrence: expect.objectContaining({
          kind: 'MONTHLY_WEEKDAY', weekdays: [], ordinal: -1,
        }),
      }),
    )
  })

  it('keeps editing open on a stale-revision API conflict', async () => {
    const view = await render()
    vi.mocked(api.updateRecurringTemplate).mockRejectedValueOnce(new Error('409'))
    await templatesTab()
    await click('Bearbeiten')
    await view.get('[data-testid="recurring-template-form"]').trigger('submit')
    await flushPromises()
    expect(view.get('[role="alert"]').text()).toContain('409')
    expect(view.find('[data-testid="recurring-template-form"]').exists()).toBe(true)
  })
})
