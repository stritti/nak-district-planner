// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ConflictError, type ConflictItem } from '../api/errors'
import * as invitationsApi from '../api/invitations'
import * as eventsApi from '../api/events'
import type { MatrixCell } from '../api/matrix'
import { useConflictStore } from '../stores/conflict'
import { useDistrictsStore } from '../stores/districts'
import { useLeadersStore } from '../stores/leaders'
import { useMatrixStore } from '../stores/matrix'
import AssignmentModal from './AssignmentModal.vue'

import { ApiError } from '../api/errors'

vi.mock('../api/invitations')
vi.mock('../api/events')

const baseCell = (overrides: Partial<MatrixCell> = {}): MatrixCell => ({
  event_id: 'event-1',
  assignment_event_id: 'event-1',
  assignment_id: null,
  assignment_status: null,
  is_gap: true,
  leader_id: null,
  leader_name: null,
  event_title: 'Gottesdienst',
  category: 'Gottesdienst',
  event_start_at: null,
  event_end_at: null,
  revision: '"rev-1"',
  ...overrides,
} as MatrixCell)

const warning: ConflictItem = {
  rule_id: 'warning-rule',
  severity: 'WARN',
  message: 'Hinweis zur Verfügbarkeit',
  details: {},
}
const blocking: ConflictItem = {
  rule_id: 'blocking-rule',
  severity: 'BLOCK',
  message: 'Nicht verfügbar',
  details: {},
}

function setup() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const matrix = useMatrixStore()
  const districts = useDistrictsStore()
  const leaders = useLeadersStore()
  const conflicts = useConflictStore()

  matrix.districtId = 'district-1'
  matrix.fromDt = '2026-10-01'
  matrix.toDt = '2026-10-31'
  districts.congregations = [
    { id: 'cong-1', name: 'Gemeinde A' },
    { id: 'cong-2', name: 'Gemeinde B' },
  ] as typeof districts.congregations
  leaders.districtId = 'district-1'
  leaders.leaders = [
    { id: 'leader-1', name: 'Anna Beispiel', rank: 'Pr.', is_active: true, assignments: [{ id: 'as-1', congregation_id: 'cong-1', role: null, is_home: true, revision: 'ar-1' }] },
    { id: 'leader-2', name: 'Bernd Muster', rank: null, is_active: true, assignments: [{ id: 'as-2', congregation_id: 'cong-2', role: null, is_home: true, revision: 'ar-2' }] },
  ] as typeof leaders.leaders

  vi.spyOn(matrix, 'fetch').mockResolvedValue(undefined)
  vi.spyOn(matrix, 'assign').mockResolvedValue(undefined)
  vi.spyOn(matrix, 'clearAssignment').mockResolvedValue(undefined)
  vi.mocked(invitationsApi.listEventInvitations).mockResolvedValue([])
  vi.mocked(invitationsApi.createInvitations).mockResolvedValue([])
  vi.mocked(invitationsApi.deleteInvitation).mockResolvedValue(undefined)
  vi.mocked(eventsApi.updateEvent).mockResolvedValue({} as never)
  vi.mocked(eventsApi.getEvent).mockResolvedValue({
    id: 'event-1', revision: '"revision-1"',
    start_at: '2026-10-05T18:00:00Z', end_at: '2026-10-05T19:30:00Z',
  } as never)

  const wrapper = mount(AssignmentModal, { global: { plugins: [pinia] } })
  const open = (cell: MatrixCell = baseCell()) => {
    ;(wrapper.vm as unknown as { open: (cell: MatrixCell, date: string, congregationName: string, congregationId: string) => void })
      .open(cell, '2026-10-05', 'Gemeinde A', 'cong-1')
  }
  return { wrapper, matrix, districts, leaders, conflicts, open }
}

async function openAndFlush(ctx: ReturnType<typeof setup>, cell = baseCell()) {
  ctx.open(cell)
  await flushPromises()
}

beforeEach(() => vi.clearAllMocks())

describe('AssignmentModal', () => {
  it('opens a gap, loads invitations and assigns a free-text leader', async () => {
    const ctx = setup()
    await openAndFlush(ctx)

    expect(invitationsApi.listEventInvitations).toHaveBeenCalledWith('event-1')
    expect(ctx.wrapper.text()).toContain('Amtstragende:n zuweisen')
    expect(ctx.wrapper.text()).toContain('05.10.2026')

    await ctx.wrapper.get('input[role="combobox"]').setValue('Freier Name')
    await ctx.wrapper.get('[data-testid="submit-assignment"]').trigger('click')
    await flushPromises()

    expect(ctx.matrix.assign).toHaveBeenCalledWith(
      'event-1',
      null,
      { leaderId: null, leaderName: 'Freier Name' },
      undefined,
      '"rev-1"',
    )
    expect(ctx.wrapper.find('.modal-backdrop').exists()).toBe(false)
  })

  it('prefills an existing leader and confirms an existing assignment', async () => {
    const ctx = setup()
    await openAndFlush(ctx, baseCell({
      is_gap: false,
      assignment_id: 'assignment-1',
      leader_id: 'leader-1',
      leader_name: 'Anna Beispiel',
    }))

    expect((ctx.wrapper.get('input[role="combobox"]').element as HTMLInputElement).value).toBe('Anna Beispiel')
    const confirm = ctx.wrapper.findAll('button').find((button) => button.text().includes('Bestaetigen'))!
    await confirm.trigger('click')
    await flushPromises()

    expect(ctx.matrix.assign).toHaveBeenCalledWith(
      'event-1',
      'assignment-1',
      { leaderId: 'leader-1', leaderName: null },
      'CONFIRMED',
      '"rev-1"',
    )
  })

  it('sends the revision of the cell it was opened with, not a later one', async () => {
    const ctx = setup()
    await openAndFlush(ctx, baseCell({ revision: '"rev-7"' }))
    await ctx.wrapper.get('input[role="combobox"]').setValue('Freier Name')
    await ctx.wrapper.get('[data-testid="submit-assignment"]').trigger('click')
    await flushPromises()
    expect(vi.mocked(ctx.matrix.assign).mock.calls[0][4]).toBe('"rev-7"')
  })

  it('never sends the cell revision for a different (host) event', async () => {
    const ctx = setup()
    await openAndFlush(ctx, baseCell({ assignment_event_id: 'host-event', revision: '"own-slot-rev"' }))
    await ctx.wrapper.get('input[role="combobox"]').setValue('Freier Name')
    await ctx.wrapper.get('[data-testid="submit-assignment"]').trigger('click')
    await flushPromises()
    expect(vi.mocked(ctx.matrix.assign).mock.calls[0][0]).toBe('host-event')
    expect(vi.mocked(ctx.matrix.assign).mock.calls[0][4]).toBe('')
  })

  it('keeps the dialog open with the server message when the event changed meanwhile (412)', async () => {
    const ctx = setup()
    vi.mocked(ctx.matrix.assign).mockRejectedValueOnce(
      new ApiError(412, 'Precondition Failed', { detail: 'Zuweisung wurde zwischenzeitlich geändert.' }),
    )
    await openAndFlush(ctx, baseCell())
    await ctx.wrapper.get('input[role="combobox"]').setValue('Freier Name')
    await ctx.wrapper.get('[data-testid="submit-assignment"]').trigger('click')
    await flushPromises()
    expect(ctx.wrapper.find('.modal-backdrop').exists()).toBe(true)
    expect(ctx.wrapper.text()).toContain('zwischenzeitlich geändert')
    expect(ctx.wrapper.text()).not.toContain('412')
    expect(ctx.matrix.fetch).toHaveBeenCalled()
    expect((ctx.wrapper.get('input[role="combobox"]').element as HTMLInputElement).value).toBe('Freier Name')
  })

  it.each([[428, 'Precondition Required'], [412, 'Precondition Failed']])(
    'shows one fixed message for %i and survives a failing background refresh',
    async (status, statusText) => {
      const ctx = setup()
      vi.mocked(ctx.matrix.assign).mockRejectedValueOnce(new ApiError(status, statusText, { detail: 'intern' }))
      vi.mocked(ctx.matrix.fetch).mockRejectedValueOnce(new Error('offline'))
      await openAndFlush(ctx, baseCell())
      await ctx.wrapper.get('input[role="combobox"]').setValue('Freier Name')
      await ctx.wrapper.get('[data-testid="submit-assignment"]').trigger('click')
      await flushPromises()
      expect(ctx.wrapper.text()).toContain('zwischenzeitlich geändert')
      expect(ctx.wrapper.text()).not.toContain('intern')
    },
  )

  it('clears an existing assignment when saving an empty edit', async () => {
    const ctx = setup()
    await openAndFlush(ctx, baseCell({ is_gap: false, assignment_id: 'assignment-1' }))

    await ctx.wrapper.get('[data-testid="submit-assignment"]').trigger('click')
    await flushPromises()

    expect(ctx.matrix.clearAssignment).toHaveBeenCalledWith('event-1', 'assignment-1', '"rev-1"')
  })

  it('requires a leader before confirming an edit', async () => {
    const ctx = setup()
    await openAndFlush(ctx, baseCell({ is_gap: false, assignment_id: 'assignment-1' }))
    const confirm = ctx.wrapper.findAll('button').find((button) => button.text().includes('Bestaetigen'))!

    // Disabled UI protects the normal path; call through DOM after providing and clearing text
    await ctx.wrapper.get('input[role="combobox"]').setValue(' ')
    expect(confirm.attributes('disabled')).toBeDefined()
  })

  it('requires warning confirmation and retries with confirmWarnings', async () => {
    const ctx = setup()
    vi.mocked(ctx.matrix.assign)
      .mockRejectedValueOnce(new ConflictError([warning]))
      .mockResolvedValueOnce(undefined)
    await openAndFlush(ctx)
    await ctx.wrapper.get('input[role="combobox"]').setValue('Anna Beispiel')

    await ctx.wrapper.get('[data-testid="submit-assignment"]').trigger('click')
    await flushPromises()

    expect(ctx.conflicts.warnings).toHaveLength(1)
    expect(ctx.conflicts.pendingAction).toBe('save')
    expect(document.body.textContent).toContain('Trotz Konflikt zuweisen?')

    const confirmButtons = Array.from(document.body.querySelectorAll('button'))
    const override = confirmButtons.find((button) => button.textContent?.includes('Trotzdem zuweisen')) as HTMLButtonElement
    override.click()
    await flushPromises()

    expect(ctx.matrix.assign).toHaveBeenLastCalledWith(
      'event-1',
      null,
      { leaderId: null, leaderName: 'Anna Beispiel', confirmWarnings: true },
      undefined,
      '"rev-1"',
    )
  })

  it('keeps blocking conflicts visible and prevents another submit', async () => {
    const ctx = setup()
    vi.mocked(ctx.matrix.assign).mockRejectedValueOnce(new ConflictError([blocking]))
    await openAndFlush(ctx)
    await ctx.wrapper.get('input[role="combobox"]').setValue('Anna Beispiel')

    await ctx.wrapper.get('[data-testid="submit-assignment"]').trigger('click')
    await flushPromises()

    expect(ctx.wrapper.text()).toContain('Nicht verfügbar')
    expect(ctx.wrapper.get('[data-testid="submit-assignment"]').attributes('disabled')).toBeDefined()
    expect(ctx.conflicts.pendingAction).toBeNull()
  })

  it('shows assignment errors without hiding the modal', async () => {
    const ctx = setup()
    vi.mocked(ctx.matrix.assign).mockRejectedValueOnce(new Error('Speichern fehlgeschlagen'))
    await openAndFlush(ctx)
    await ctx.wrapper.get('input[role="combobox"]').setValue('Anna Beispiel')

    await ctx.wrapper.get('[data-testid="submit-assignment"]').trigger('click')
    await flushPromises()

    expect(ctx.wrapper.text()).toContain('Speichern fehlgeschlagen')
    expect(ctx.wrapper.find('.modal-backdrop').exists()).toBe(true)
  })

  it('creates district and external invitations and reloads invitation state', async () => {
    const ctx = setup()
    await openAndFlush(ctx)
    const selects = ctx.wrapper.findAll('select')

    await selects[0].setValue('DISTRICT_CONGREGATION')
    await ctx.wrapper.findAll('select')[1].setValue('cong-2')
    const invitationButton = ctx.wrapper.findAll('button').find((button) => button.text().includes('Einladung anlegen'))!
    await invitationButton.trigger('click')
    await flushPromises()
    expect(invitationsApi.createInvitations).toHaveBeenCalledWith('event-1', [{
      target_type: 'DISTRICT_CONGREGATION',
      target_congregation_id: 'cong-2',
    }])

    await ctx.wrapper.findAll('select')[0].setValue('EXTERNAL_NOTE')
    await ctx.wrapper.get('input[placeholder="z. B. Einladung in Nachbarbezirk"]').setValue('Nachbarbezirk')
    await invitationButton.trigger('click')
    await flushPromises()
    expect(invitationsApi.createInvitations).toHaveBeenLastCalledWith('event-1', [{
      target_type: 'EXTERNAL_NOTE',
      external_target_note: 'Nachbarbezirk',
    }])
    expect(ctx.matrix.fetch).toHaveBeenCalled()
  })

  it('loads, reuses and deletes existing invitations', async () => {
    vi.mocked(invitationsApi.listEventInvitations).mockResolvedValueOnce([
      {
        id: 'inv-1',
        source_event_id: 'event-1',
        source_congregation_id: 'cong-1',
        target_type: 'DISTRICT_CONGREGATION',
        target_congregation_id: 'cong-2',
        external_target_note: null,
        linked_event_id: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ]).mockResolvedValue([])
    const ctx = setup()
    // setup installs a default; restore the desired first response afterwards
    vi.mocked(invitationsApi.listEventInvitations).mockResolvedValueOnce([
      {
        id: 'inv-1', source_event_id: 'event-1', source_congregation_id: 'cong-1',
        target_type: 'DISTRICT_CONGREGATION', target_congregation_id: 'cong-2',
        external_target_note: null, linked_event_id: null,
        created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
      },
    ]).mockResolvedValue([])
    await openAndFlush(ctx)

    expect(ctx.wrapper.text()).toContain('Gemeinde: Gemeinde B')
    const existingButton = ctx.wrapper.findAll('button').find((button) => button.text().includes('Gemeinde: Gemeinde B'))!
    await existingButton.trigger('click')
    expect((ctx.wrapper.findAll('select')[0].element as HTMLSelectElement).value).toBe('DISTRICT_CONGREGATION')

    const deleteButton = ctx.wrapper.findAll('button').find((button) => button.text() === 'Loeschen')!
    await deleteButton.trigger('click')
    await flushPromises()
    expect(invitationsApi.deleteInvitation).toHaveBeenCalledWith('inv-1')
  })

  it('shows invitation load/save/delete errors', async () => {
    const ctx = setup()
    vi.mocked(invitationsApi.listEventInvitations).mockRejectedValueOnce(new Error('Einladungen kaputt'))
    await openAndFlush(ctx)
    expect(ctx.wrapper.text()).toContain('Einladungen kaputt')

    vi.mocked(invitationsApi.createInvitations).mockRejectedValueOnce(new Error('Invite save failed'))
    await ctx.wrapper.findAll('select')[0].setValue('EXTERNAL_NOTE')
    await ctx.wrapper.get('input[placeholder="z. B. Einladung in Nachbarbezirk"]').setValue('Extern')
    const invitationButton = ctx.wrapper.findAll('button').find((button) => button.text().includes('Einladung anlegen'))!
    await invitationButton.trigger('click')
    await flushPromises()
    expect(ctx.wrapper.text()).toContain('Invite save failed')
  })

  it('moves a service with duration and validates invalid duration', async () => {
    const ctx = setup()
    await openAndFlush(ctx, baseCell({
      event_start_at: '2026-10-05T18:00:00Z',
      event_end_at: '2026-10-05T19:30:00Z',
    }))
    const moveButton = ctx.wrapper.findAll('button').find((button) => button.text().includes('Termin verschieben'))!
    const duration = ctx.wrapper.get('input[type="number"]')

    await duration.setValue(10)
    await moveButton.trigger('click')
    expect(ctx.wrapper.text()).toContain('mindestens 15 Minuten')
    expect(eventsApi.updateEvent).not.toHaveBeenCalled()

    await duration.setValue(60)
    await moveButton.trigger('click')
    await flushPromises()
    expect(eventsApi.updateEvent).toHaveBeenCalledWith(
      'event-1',
      expect.objectContaining({ start_at: expect.any(String), end_at: expect.any(String) }),
      '"revision-1"',
    )
    expect(ctx.matrix.fetch).toHaveBeenCalled()
  })

  it('removes an existing assignment from the dedicated remove action', async () => {
    const ctx = setup()
    await openAndFlush(ctx, baseCell({ is_gap: false, assignment_id: 'assignment-1' }))
    const remove = ctx.wrapper.findAll('button').find((button) => button.text() === 'Entfernen')!

    await remove.trigger('click')
    await flushPromises()

    expect(ctx.matrix.clearAssignment).toHaveBeenCalledWith('event-1', 'assignment-1', '"rev-1"')
    expect(ctx.wrapper.find('.modal-backdrop').exists()).toBe(false)
  })

  it.each([[412, 'Precondition Failed'], [428, 'Precondition Required']])(
    'refreshes the matrix and explains a stale event (%i) when removing',
    async (status, statusText) => {
      const ctx = setup()
      vi.mocked(ctx.matrix.clearAssignment).mockRejectedValueOnce(
        new ApiError(status, statusText, { detail: 'intern' }),
      )
      await openAndFlush(ctx, baseCell({ is_gap: false, assignment_id: 'assignment-1' }))
      const remove = ctx.wrapper.findAll('button').find((button) => button.text() === 'Entfernen')!
      vi.mocked(ctx.matrix.fetch).mockClear()

      await remove.trigger('click')
      await flushPromises()

      expect(ctx.wrapper.find('.modal-backdrop').exists()).toBe(true)
      expect(ctx.wrapper.text()).toContain('zwischenzeitlich geändert')
      expect(ctx.wrapper.text()).not.toContain('intern')
      expect(ctx.matrix.fetch).toHaveBeenCalledOnce()
    },
  )

  it('shows other removal errors unchanged and does not refresh the matrix', async () => {
    const ctx = setup()
    vi.mocked(ctx.matrix.clearAssignment).mockRejectedValueOnce(new Error('Entfernen kaputt'))
    await openAndFlush(ctx, baseCell({ is_gap: false, assignment_id: 'assignment-1' }))
    const remove = ctx.wrapper.findAll('button').find((button) => button.text() === 'Entfernen')!
    vi.mocked(ctx.matrix.fetch).mockClear()
    await remove.trigger('click')
    await flushPromises()
    expect(ctx.wrapper.text()).toContain('Entfernen kaputt')
    expect(ctx.matrix.fetch).not.toHaveBeenCalled()
  })
})
