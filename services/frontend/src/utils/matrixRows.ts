import type { MatrixRow } from '../api/matrix'

export type MatrixSortMode = 'default' | 'grouped'

export function sortMatrixRows(rows: MatrixRow[], mode: MatrixSortMode): MatrixRow[] {
  if (mode !== 'grouped') {
    return rows
  }

  return rows.slice().sort((a, b) => {
    const aGroup = (a.group_name ?? '').trim().toLocaleLowerCase('de')
    const bGroup = (b.group_name ?? '').trim().toLocaleLowerCase('de')

    if (aGroup && bGroup && aGroup !== bGroup) {
      return aGroup.localeCompare(bGroup, 'de')
    }
    if (aGroup && !bGroup) return -1
    if (!aGroup && bGroup) return 1

    return a.congregation_name.localeCompare(b.congregation_name, 'de')
  })
}
