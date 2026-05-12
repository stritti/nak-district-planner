import { describe, expect, it } from 'vitest'

import type { MatrixRow } from '../api/matrix'
import { sortMatrixRows } from './matrixRows'

function row(name: string, groupName?: string | null): MatrixRow {
  return {
    congregation_id: name,
    congregation_name: name,
    group_id: groupName ? `${groupName}-id` : null,
    group_name: groupName ?? null,
    cells: {},
  }
}

describe('sortMatrixRows', () => {
  it('returns unchanged input for default mode', () => {
    const rows = [row('B'), row('A')]
    expect(sortMatrixRows(rows, 'default')).toBe(rows)
  })

  it('sorts by group then congregation name in grouped mode', () => {
    const rows = [
      row('Beta', null),
      row('Alpha', 'Ring B'),
      row('Gamma', 'Ring A'),
      row('Delta', 'Ring A'),
    ]

    const sorted = sortMatrixRows(rows, 'grouped')
    expect(sorted.map((entry) => entry.congregation_name)).toEqual(['Delta', 'Gamma', 'Alpha', 'Beta'])
  })
})
