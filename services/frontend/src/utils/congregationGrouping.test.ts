import { describe, expect, it } from 'vitest'

import type { CongregationGroupResponse, CongregationResponse } from '@/api/districts'
import { buildCongregationSections } from './congregationGrouping'

function congregation(
  id: string,
  name: string,
  groupId: string | null,
  groupName: string | null = null,
): CongregationResponse {
  return {
    id,
    name,
    district_id: 'district-1',
    group_id: groupId,
    group_name: groupName,
    service_times: [],
    created_at: '2026-04-01T00:00:00Z',
    updated_at: '2026-04-01T00:00:00Z',
  }
}

function group(id: string, name: string): CongregationGroupResponse {
  return {
    id,
    name,
    district_id: 'district-1',
    created_at: '2026-04-01T00:00:00Z',
    updated_at: '2026-04-01T00:00:00Z',
  }
}

describe('buildCongregationSections', () => {
  it('groups congregations and keeps ungrouped section', () => {
    const sections = buildCongregationSections(
      [
        congregation('c1', 'Nord', 'g1'),
        congregation('c2', 'Sued', null),
        congregation('c3', 'West', 'g1'),
      ],
      [group('g1', 'Ring A')],
    )

    expect(sections).toHaveLength(2)
    expect(sections[0].title).toBe('Ring A')
    expect(sections[0].items.map((item) => item.name)).toEqual(['Nord', 'West'])
    expect(sections[1].title).toBe('Ohne Gruppe')
    expect(sections[1].items.map((item) => item.name)).toEqual(['Sued'])
  })

  it('falls back to congregation group_name when group catalog is outdated', () => {
    const sections = buildCongregationSections(
      [congregation('c1', 'Mitte', 'ghost', 'Sondergruppe')],
      [],
    )

    expect(sections).toHaveLength(1)
    expect(sections[0].title).toBe('Sondergruppe')
  })
})
