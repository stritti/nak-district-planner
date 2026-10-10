// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { MatrixRow } from '../api/matrix'

export type MatrixSortMode = 'default' | 'grouped'

export function sortMatrixRows(rows: MatrixRow[], mode: MatrixSortMode): MatrixRow[] {
  if (mode !== 'grouped') {
    return rows
  }

  return rows.slice().sort((a, b) => {
    const aGroup = (a.group_name ?? '').trim().toLowerCase()
    const bGroup = (b.group_name ?? '').trim().toLowerCase()

    if (aGroup && bGroup && aGroup !== bGroup) {
      return aGroup.localeCompare(bGroup, 'de')
    }
    if (aGroup && !bGroup) return -1
    if (!aGroup && bGroup) return 1

    return a.congregation_name.localeCompare(b.congregation_name, 'de')
  })
}

/** Case- and diacritic-insensitive form, so "zurich" finds "Zürich". */
function searchKey(text: string): string {
  return text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('de')
}

/** Rows whose congregation (or group) name contains the query; blank query keeps all. */
export function filterMatrixRows(rows: MatrixRow[], query: string): MatrixRow[] {
  const needle = searchKey(query.trim())
  if (!needle) return rows
  return rows.filter((row) =>
    [row.congregation_name, row.group_name ?? ''].some((name) => searchKey(name).includes(needle)),
  )
}
