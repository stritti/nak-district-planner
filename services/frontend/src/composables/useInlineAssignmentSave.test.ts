// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/errors'
import { changeAssignmentInline, type InlineAssignmentResult } from '../api/serviceAssignments'
import { useInlineAssignmentSave } from './useInlineAssignmentSave'

const mocks = vi.hoisted(() => ({ confirm: vi.fn() }))
vi.mock('../api/serviceAssignments', () => ({ changeAssignmentInline: vi.fn() }))
vi.mock('./useConfirm', () => ({ useConfirm: () => mocks.confirm }))

const saved: InlineAssignmentResult = {
  id: 'a1', event_id: 'e1', leader_id: 'l1', leader_name: null,
  status: 'ASSIGNED', event_revision: '"rev-2"', created_at: '', updated_at: '',
}
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

beforeEach(() => {
  vi.resetAllMocks()
})

describe('useInlineAssignmentSave', () => {
  it('returns the authoritative response with the original revision', async () => {
    vi.mocked(changeAssignmentInline).mockResolvedValue(saved)
    await expect(useInlineAssignmentSave()('e1', 'l1', revision)).resolves.toEqual(saved)
    expect(changeAssignmentInline).toHaveBeenCalledWith('e1', 'l1', revision)
    expect(mocks.confirm).not.toHaveBeenCalled()
  })

  it('retries warning-only conflicts once after explicit confirmation', async () => {
    vi.mocked(changeAssignmentInline).mockRejectedValueOnce(conflict('PASS', 'WARN')).mockResolvedValueOnce(saved)
    mocks.confirm.mockResolvedValue(true)
    await expect(useInlineAssignmentSave()('e1', 'l1', revision)).resolves.toEqual(saved)
    expect(mocks.confirm).toHaveBeenCalledWith(expect.objectContaining({
      message: 'Konflikt WARN', variant: 'warning',
    }))
    expect(changeAssignmentInline).toHaveBeenLastCalledWith('e1', 'l1', revision, true)
    expect(changeAssignmentInline).toHaveBeenCalledTimes(2)
  })

  it('keeps the failure without retry when the user cancels', async () => {
    vi.mocked(changeAssignmentInline).mockRejectedValue(conflict('WARN'))
    mocks.confirm.mockResolvedValue(false)
    await expect(useInlineAssignmentSave()('e1', 'l1', revision)).rejects.toThrow('abgebrochen')
    expect(changeAssignmentInline).toHaveBeenCalledOnce()
  })

  it.each([
    ['BLOCK'], ['WARN', 'BLOCK'], ['UNKNOWN'], ['WARN', 'UNKNOWN'], ['PASS'], [],
  ])('never acknowledges non-warning conflict list %j', async (...severities: string[]) => {
    const error = conflict(...severities)
    vi.mocked(changeAssignmentInline).mockRejectedValue(error)
    await expect(useInlineAssignmentSave()('e1', 'l1', revision)).rejects.toBe(error)
    expect(mocks.confirm).not.toHaveBeenCalled()
    expect(changeAssignmentInline).toHaveBeenCalledOnce()
  })

  it.each([403, 412, 422, 500])('propagates status %s without a confirmation', async (status) => {
    const error = new ApiError(status, 'Failure', {})
    vi.mocked(changeAssignmentInline).mockRejectedValue(error)
    await expect(useInlineAssignmentSave()('e1', 'l1', revision)).rejects.toBe(error)
    expect(mocks.confirm).not.toHaveBeenCalled()
  })

  it('propagates a failed confirmed retry without looping', async () => {
    const error = conflict('BLOCK')
    vi.mocked(changeAssignmentInline).mockRejectedValueOnce(conflict('WARN')).mockRejectedValueOnce(error)
    mocks.confirm.mockResolvedValue(true)
    await expect(useInlineAssignmentSave()('e1', 'l1', revision)).rejects.toBe(error)
    expect(mocks.confirm).toHaveBeenCalledOnce()
    expect(changeAssignmentInline).toHaveBeenCalledTimes(2)
  })
})
