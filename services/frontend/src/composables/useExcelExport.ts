import writeXlsxFile from 'write-excel-file/browser'
import type { Row, Cell } from 'write-excel-file/browser'
import type { MatrixResponse } from '@/api/matrix'
import type { EventResponse } from '@/api/events'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-')
  return `${day}.${month}.${year}`
}

function formatDateTime(isoString: string): string {
  // Display times in the user's local timezone using Intl
  return new Intl.DateTimeFormat('de-DE', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }).format(new Date(isoString))
}

function headerCell(value: string): Cell {
  return { value, fontWeight: 'bold', backgroundColor: '#3B82F6', textColor: '#FFFFFF' }
}

function holidayHeaderCell(value: string): Cell {
  return { value, fontWeight: 'bold', backgroundColor: '#FEF3C7', textColor: '#92400E' }
}

function gapCell(value: string): Cell {
  return { value, backgroundColor: '#FEE2E2', textColor: '#B91C1C' }
}

// ── Matrix Export ─────────────────────────────────────────────────────────────

export async function exportMatrixToExcel(
  matrix: MatrixResponse,
  fromDt: string,
  toDt: string,
): Promise<void> {
  const headerRow: Row = [
    headerCell('Gemeinde'),
    ...matrix.dates.map((d) => {
      const isHoliday = (matrix.holidays[d]?.length ?? 0) > 0
      const label = isHoliday
        ? `${formatDate(d)}\n${matrix.holidays[d].join(', ')}`
        : formatDate(d)
      return isHoliday ? holidayHeaderCell(label) : headerCell(label)
    }),
  ]

  const dataRows: Row[] = matrix.rows.map((row) => [
    { value: row.congregation_name, fontWeight: 'bold' } as Cell,
    ...matrix.dates.map((d): Cell => {
      const cell = row.cells[d]
      if (!cell?.event_id) return { value: '–' }
      if (cell.is_gap) return gapCell('LÜCKE')
      const parts: string[] = []
      if (cell.event_title) parts.push(cell.event_title)
      if (cell.leader_name)  parts.push(cell.leader_name)
      return { value: parts.join('\n') }
    }),
  ])

  const columns = [
    { width: 20 },
    ...matrix.dates.map(() => ({ width: 18 })),
  ]

  const fileName = `Dienstplan-Matrix_${fromDt}_${toDt}.xlsx`
  await writeXlsxFile([headerRow, ...dataRows], { columns, fileName })
}

// ── Events Export ─────────────────────────────────────────────────────────────

export async function exportEventsToExcel(
  events: EventResponse[],
  fileName = 'Ereignisse.xlsx',
): Promise<void> {
  const STATUS_LABELS: Record<string, string> = {
    DRAFT: 'Entwurf',
    PUBLISHED: 'Veröffentlicht',
    CANCELLED: 'Abgesagt',
  }

  const SOURCE_LABELS: Record<string, string> = {
    INTERNAL: 'Intern',
    EXTERNAL: 'Extern',
  }

  const headerRow: Row = [
    headerCell('Titel'),
    headerCell('Beginn'),
    headerCell('Ende'),
    headerCell('Kategorie'),
    headerCell('Status'),
    headerCell('Quelle'),
  ]

  const dataRows: Row[] = events.map((e): Row => [
    { value: e.title },
    { value: formatDateTime(e.start_at) },
    { value: formatDateTime(e.end_at) },
    { value: e.category ?? '' },
    { value: STATUS_LABELS[e.status] ?? e.status },
    { value: SOURCE_LABELS[e.source] ?? e.source },
  ])

  const columns = [
    { width: 32 },
    { width: 18 },
    { width: 18 },
    { width: 18 },
    { width: 16 },
    { width: 12 },
  ]

  await writeXlsxFile([headerRow, ...dataRows], { columns, fileName })
}
