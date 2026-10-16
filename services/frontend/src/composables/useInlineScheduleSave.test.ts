// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/errors'
import { updateEvent, type EventResponse } from '../api/events'
import { toLocalInputValue, useInlineScheduleSave } from './useInlineScheduleSave'

const mocks = vi.hoisted(() => ({ confirm: vi.fn() }))
vi.mock('../api/events', () => ({ updateEvent: vi.fn() }))
vi.mock('./useConfirm', () => ({ useConfirm: () => mocks.confirm }))

const event = {
  id: 'e1',
  start_at: '2026-10-18T09:30:00.000Z',
  end_at: '2026-10-18T11:00:00.000Z',
} as EventResponse
const saved = { ...event, revision: '"rev-2"' } as EventResponse
const revision = '"rev-1"'

function conflict(...severities: string[]) {
  return new ApiError(409, 'Conflict', {
    detail: {
      conflicts: severities.map((severity) => ({
        rule_id: 'R1', severity, message: `Konflikt ${severity}`, details: {},
      })),
    },
  })
}

beforeEach(() => vi.resetAllMocks())

describe('toLocalInputValue', () => {
  it('formats an ISO timestamp for datetime-local inputs in local time', () => {
    const local = new Date(2026, 9, 18, 9, 5)
    expect(toLocalInputValue(local.toISOString())).toBe('2026-10-18T09:05')
  })
})

describe('useInlineScheduleSave', () => {
  it('moves start and end together and keeps the duration', async () => {
    vi.mocked(updateEvent).mockResolvedValue(saved)
    const draft = '2026-10-25T10:00'
    await expect(useInlineScheduleSave()(event, draft, revision)).resolves.toEqual(saved)
    const start = new Date(draft)
    const end = new Date(start.getTime() + 90 * 60_000)
    expect(updateEvent).toHaveBeenCalledWith(
      'e1', { start_at: start.toISOString(), end_at: end.toISOString() }, revision,
    )
    expect(mocks.confirm).not.toHaveBeenCalled()
  })

  it('rejects an unparsable value without calling the API', async () => {
    await expect(useInlineScheduleSave()(event, 'nonsense', revision)).rejects.toThrow('Ungültiges Datum')
    expect(updateEvent).not.toHaveBeenCalled()
  })

  it('retries warning-only conflicts once after explicit confirmation', async () => {
    vi.mocked(updateEvent).mockRejectedValueOnce(conflict('WARN')).mockResolvedValueOnce(saved)
    mocks.confirm.mockResolvedValue(true)
    await expect(useInlineScheduleSave()(event, '2026-10-25T10:00', revision)).resolves.toEqual(saved)
    expect(mocks.confirm).toHaveBeenCalledWith(expect.objectContaining({ message: 'Konflikt WARN', variant: 'warning' }))
    expect(updateEvent).toHaveBeenLastCalledWith('e1', expect.objectContaining({ confirm_warnings: true }), revision)
  })

  it('keeps the failure without retry when the user cancels', async () => {
    vi.mocked(updateEvent).mockRejectedValue(conflict('WARN'))
    mocks.confirm.mockResolvedValue(false)
    await expect(useInlineScheduleSave()(event, '2026-10-25T10:00', revision)).rejects.toThrow('abgebrochen')
    expect(updateEvent).toHaveBeenCalledOnce()
  })

  it.each([['BLOCK'], ['WARN', 'BLOCK'], ['PASS'], []])('never prompts for non-warning conflicts %j', async (...severities) => {
    const failure = conflict(...severities)
    vi.mocked(updateEvent).mockRejectedValue(failure)
    await expect(useInlineScheduleSave()(event, '2026-10-25T10:00', revision)).rejects.toBe(failure)
    expect(mocks.confirm).not.toHaveBeenCalled()
  })

  it('propagates stale revisions (412) unchanged', async () => {
    const stale = new ApiError(412, 'Precondition Failed', { detail: 'alt' })
    vi.mocked(updateEvent).mockRejectedValue(stale)
    await expect(useInlineScheduleSave()(event, '2026-10-25T10:00', revision)).rejects.toBe(stale)
    expect(mocks.confirm).not.toHaveBeenCalled()
  })
})
