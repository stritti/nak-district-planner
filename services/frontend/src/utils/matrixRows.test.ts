// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'

import type { MatrixRow } from '../api/matrix'
import { filterMatrixRows, sortMatrixRows } from './matrixRows'

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

describe('filterMatrixRows', () => {
  const rows = [row('Zürich-Nord', 'Ring A'), row('Basel'), row('Bern', 'Ring B')]

  it.each(['', '   '])('keeps all rows for a blank query (%j)', (query) => {
    expect(filterMatrixRows(rows, query)).toBe(rows)
  })

  it('matches case- and diacritic-insensitively on the congregation name', () => {
    expect(filterMatrixRows(rows, '  ZURICH ').map((r) => r.congregation_name)).toEqual(['Zürich-Nord'])
  })

  it('matches on the group name', () => {
    expect(filterMatrixRows(rows, 'ring b').map((r) => r.congregation_name)).toEqual(['Bern'])
  })

  it('returns an empty list when nothing matches', () => {
    expect(filterMatrixRows(rows, 'Hamburg')).toEqual([])
  })
})
