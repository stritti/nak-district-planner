import { describe, expect, it } from 'vitest'
import { notificationDestination } from './notificationLinks'

const candidateId = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'

describe('notificationDestination', () => {
  it('resolves candidate review notifications to an internal route', () => {
    expect(notificationDestination({
      type: 'CANDIDATE_REVIEW',
      payload: { candidate_id: candidateId },
    })).toBe(`/admin/external-candidates?candidate_id=${candidateId}`)
  })

  it('accepts a reference ID when no candidate ID is provided', () => {
    expect(notificationDestination({
      type: 'EXTERNAL_EVENT_DETECTED',
      payload: { reference_id: candidateId },
    })).toBe(`/admin/external-candidates?candidate_id=${candidateId}`)
  })

  it.each([
    { type: 'SYSTEM', payload: { candidate_id: candidateId } },
    { type: 'CANDIDATE_REVIEW', payload: {} },
    { type: 'CANDIDATE_REVIEW', payload: { candidate_id: 'javascript:alert(1)' } },
    { type: 'CANDIDATE_REVIEW', payload: { candidate_id: '../logout' } },
    { type: 'CANDIDATE_REVIEW', payload: { candidate_id: 123 } },
    { type: 'CANDIDATE_REVIEW', payload: { candidate_id: null } },
    { type: 'CANDIDATE_REVIEW', payload: { candidate_id: 'bad', reference_id: candidateId } },
    { type: 'CANDIDATE_REVIEW', payload: { url: 'https://hostile.example' } },
  ])('rejects unsupported or unsafe payload: %j', (item) => {
    expect(notificationDestination(item)).toBeNull()
  })
})
