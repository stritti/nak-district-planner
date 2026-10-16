// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/errors'
import { previewEventChange, updateEvent, type EventChangeImpact, type EventResponse } from '../api/events'
import { useInlineScopeSave } from './useInlineScopeSave'

const mocks = vi.hoisted(() => ({ confirm: vi.fn() }))
vi.mock('../api/events', () => ({ previewEventChange: vi.fn(), updateEvent: vi.fn() }))
vi.mock('./useConfirm', () => ({ useConfirm: () => mocks.confirm }))

const event = { id: 'e1', category: 'Gottesdienst', congregation_id: 'c1' } as EventResponse
const saved = { ...event, revision: '"rev-2"' } as EventResponse
const revision = '"rev-1"'

function impact(overrides: Partial<EventChangeImpact> = {}): EventChangeImpact {
  return {
    blocked: false, requires_confirmation: false, items: [],
    duties_newly_flagged: 0, duties_newly_quarantined: 0, duties_flagged_after: 0, duties_quarantined_after: 0,
    ...overrides,
  }
}

beforeEach(() => vi.resetAllMocks())

describe('useInlineScopeSave category', () => {
  it('previews, then patches with the same revision when nothing is affected', async () => {
    vi.mocked(previewEventChange).mockResolvedValue(impact())
    vi.mocked(updateEvent).mockResolvedValue(saved)
    await expect(useInlineScopeSave().saveCategory(event, 'Feiertag', revision)).resolves.toEqual(saved)
    expect(previewEventChange).toHaveBeenCalledWith('e1', { category: 'Feiertag' }, revision)
    expect(updateEvent).toHaveBeenCalledWith('e1', {
      category: 'Feiertag', acknowledged_duty_impact: { newly_flagged: 0, newly_quarantined: 0 },
    }, revision)
    expect(mocks.confirm).not.toHaveBeenCalled()
  })

  it('stores an empty category as null', async () => {
    vi.mocked(previewEventChange).mockResolvedValue(impact())
    vi.mocked(updateEvent).mockResolvedValue(saved)
    await useInlineScopeSave().saveCategory(event, '', revision)
    expect(updateEvent).toHaveBeenCalledWith('e1', expect.objectContaining({ category: null }), revision)
  })

  it('asks for confirmation when duties would need review and aborts on cancel', async () => {
    vi.mocked(previewEventChange).mockResolvedValue(impact({ duties_newly_flagged: 2 }))
    mocks.confirm.mockResolvedValue(false)
    await expect(useInlineScopeSave().saveCategory(event, 'Feiertag', revision)).rejects.toThrow('abgebrochen')
    expect(mocks.confirm).toHaveBeenCalledWith(expect.objectContaining({
      message: expect.stringContaining('2'), variant: 'warning',
    }))
    expect(updateEvent).not.toHaveBeenCalled()
  })

  it('patches after the duty review was acknowledged', async () => {
    vi.mocked(previewEventChange).mockResolvedValue(impact({ duties_newly_flagged: 1 }))
    mocks.confirm.mockResolvedValue(true)
    vi.mocked(updateEvent).mockResolvedValue(saved)
    await useInlineScopeSave().saveCategory(event, 'Feiertag', revision)
    expect(updateEvent).toHaveBeenCalledOnce()
  })

  it('does not call the API when the category is unchanged', async () => {
    await expect(useInlineScopeSave().saveCategory(event, 'Gottesdienst', revision)).resolves.toEqual(event)
    expect(previewEventChange).not.toHaveBeenCalled()
  })
})

describe('useInlineScopeSave congregation', () => {
  it('moves to the district level with a null congregation', async () => {
    vi.mocked(previewEventChange).mockResolvedValue(impact())
    vi.mocked(updateEvent).mockResolvedValue(saved)
    await useInlineScopeSave().saveCongregation(event, '', revision)
    expect(previewEventChange).toHaveBeenCalledWith('e1', { congregation_id: null }, revision)
    expect(updateEvent).toHaveBeenCalledWith('e1', expect.objectContaining({ congregation_id: null }), revision)
  })

  it('mentions quarantine in the confirmation and acknowledges warnings', async () => {
    vi.mocked(previewEventChange).mockResolvedValue(impact({
      duties_newly_flagged: 1, duties_newly_quarantined: 1, duties_quarantined_after: 1, requires_confirmation: true,
      items: [{ assignment_id: 'a', leader_id: 'l', conflicts: [{ rule_id: 'R', severity: 'WARN', message: 'Dienstende', details: {} }] }],
    }))
    mocks.confirm.mockResolvedValue(true)
    vi.mocked(updateEvent).mockResolvedValue(saved)
    await useInlineScopeSave().saveCongregation(event, 'c2', revision)
    expect(mocks.confirm.mock.calls[0][0].message).toMatch(/Dienstende/)
    expect(mocks.confirm.mock.calls[0][0].message).toMatch(/ausgeblendet/)
    expect(updateEvent).toHaveBeenCalledWith('e1', {
      congregation_id: 'c2', confirm_warnings: true,
      acknowledged_duty_impact: { newly_flagged: 1, newly_quarantined: 1 },
    }, revision)
  })

  it('refuses blocked moves without patching or prompting', async () => {
    vi.mocked(previewEventChange).mockResolvedValue(impact({
      blocked: true,
      items: [{ assignment_id: 'a', leader_id: 'l', conflicts: [{ rule_id: 'R', severity: 'BLOCK', message: 'Dienstende überschritten', details: {} }] }],
    }))
    await expect(useInlineScopeSave().saveCongregation(event, 'c2', revision)).rejects.toThrow('Dienstende überschritten')
    expect(mocks.confirm).not.toHaveBeenCalled()
    expect(updateEvent).not.toHaveBeenCalled()
  })

  it('propagates stale previews (412) unchanged', async () => {
    const stale = new ApiError(412, 'Precondition Failed', { detail: 'alt' })
    vi.mocked(previewEventChange).mockRejectedValue(stale)
    await expect(useInlineScopeSave().saveCongregation(event, 'c2', revision)).rejects.toBe(stale)
    expect(updateEvent).not.toHaveBeenCalled()
  })
  it('asks for confirmation when only a quarantine is new (duty was already in review)', async () => {
    vi.mocked(previewEventChange).mockResolvedValue(impact({
      duties_newly_flagged: 0, duties_newly_quarantined: 1, duties_flagged_after: 1, duties_quarantined_after: 1,
    }))
    mocks.confirm.mockResolvedValue(true)
    vi.mocked(updateEvent).mockResolvedValue(saved)
    await useInlineScopeSave().saveCongregation(event, 'c2', revision)
    expect(mocks.confirm.mock.calls[0][0].message).toMatch(/1 Dienst\(e\) werden in der neuen Gemeinde ausgeblendet/)
    expect(updateEvent).toHaveBeenCalledWith('e1', expect.objectContaining({
      acknowledged_duty_impact: { newly_flagged: 0, newly_quarantined: 1 },
    }), revision)
  })

  it('surfaces a server-side duty impact rejection instead of retrying silently', async () => {
    vi.mocked(previewEventChange).mockResolvedValue(impact())
    const rejected = new ApiError(409, 'Conflict', {
      detail: { code: 'duty_impact_unacknowledged', message: 'Bitte die Auswirkungen erneut prüfen und bestätigen.' },
    })
    vi.mocked(updateEvent).mockRejectedValue(rejected)
    await expect(useInlineScopeSave().saveCategory(event, 'Feiertag', revision)).rejects.toBe(rejected)
    expect(updateEvent).toHaveBeenCalledOnce()
  })
})
