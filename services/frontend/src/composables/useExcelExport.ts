/**
 * Minimal XLSX (.xlsx) writer — no external dependencies.
 * Generates a ZIP archive (Store method, no compression) with OOXML SpreadsheetML XML.
 */
import type { MatrixResponse } from '../api/matrix'
import type { EventResponse } from '../api/events'

// ── Date/time formatting ──────────────────────────────────────────────────────

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat('de-DE', {
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit',
})

function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-')
  return `${day}.${month}.${year}`
}

function formatDateTime(isoString: string): string {
  return DATE_TIME_FORMATTER.format(new Date(isoString))
}

// ── Cell style indices ────────────────────────────────────────────────────────
// Indices map to cellXfs entries in styles.xml:
// 0 = default, 1 = blue header, 2 = amber header, 3 = gap cell, 4 = bold text

const STYLE_HEADER_BLUE  = 1
const STYLE_HEADER_AMBER = 2
const STYLE_GAP          = 3
const STYLE_BOLD         = 4

interface XlsxCell { value: string | number | null; style?: number }
type XlsxRow = XlsxCell[]

// ── XML helpers ───────────────────────────────────────────────────────────────

function escXml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

// ── XLSX XML fragments ────────────────────────────────────────────────────────

function contentTypesXml(): string {
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    + '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    + '<Default Extension="xml" ContentType="application/xml"/>'
    + '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    + '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    + '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
    + '</Types>'
}

function rootRelsXml(): string {
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    + '</Relationships>'
}

function workbookRelsXml(): string {
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    + '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    + '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
    + '</Relationships>'
}

function workbookXml(sheetName: string): string {
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    + ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    + `<sheets><sheet name="${escXml(sheetName)}" sheetId="1" r:id="rId1"/></sheets>`
    + '</workbook>'
}

function stylesXml(): string {
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    + '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    + '<fonts count="5">'
    +   '<font><sz val="11"/><name val="Calibri"/></font>'
    +   '<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font>'
    +   '<font><b/><sz val="11"/><name val="Calibri"/><color rgb="FF92400E"/></font>'
    +   '<font><sz val="11"/><name val="Calibri"/><color rgb="FFB91C1C"/></font>'
    +   '<font><b/><sz val="11"/><name val="Calibri"/></font>'
    + '</fonts>'
    + '<fills count="5">'
    +   '<fill><patternFill patternType="none"/></fill>'
    +   '<fill><patternFill patternType="gray125"/></fill>'
    +   '<fill><patternFill patternType="solid"><fgColor rgb="FF3B82F6"/><bgColor indexed="64"/></patternFill></fill>'
    +   '<fill><patternFill patternType="solid"><fgColor rgb="FFFEF3C7"/><bgColor indexed="64"/></patternFill></fill>'
    +   '<fill><patternFill patternType="solid"><fgColor rgb="FFFEE2E2"/><bgColor indexed="64"/></patternFill></fill>'
    + '</fills>'
    + '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    + '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    + '<cellXfs count="5">'
    +   '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    +   '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
    +   '<xf numFmtId="0" fontId="2" fillId="3" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
    +   '<xf numFmtId="0" fontId="3" fillId="4" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
    +   '<xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    + '</cellXfs>'
    + '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    + '</styleSheet>'
}

function sharedStringsXml(strings: string[]): string {
  const items = strings
    .map((s) => `<si><t xml:space="preserve">${escXml(s)}</t></si>`)
    .join('')
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    + `<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"`
    + ` count="${strings.length}" uniqueCount="${strings.length}">${items}</sst>`
}

function colLetter(zeroBasedIdx: number): string {
  let n = zeroBasedIdx + 1
  let s = ''
  while (n > 0) { n--; s = String.fromCharCode(65 + (n % 26)) + s; n = Math.floor(n / 26) }
  return s
}

function worksheetXml(
  rows: XlsxRow[],
  colWidths: number[],
  stringIndex: Map<string, number>,
): string {
  const colsXml = colWidths
    .map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`)
    .join('')

  const rowsXml = rows.map((row, ri) => {
    const cells = row.map((cell, ci) => {
      const addr = `${colLetter(ci)}${ri + 1}`
      const s = cell.style !== undefined ? ` s="${cell.style}"` : ''
      if (cell.value === null || cell.value === undefined || cell.value === '') {
        return `<c r="${addr}"${s}/>`
      }
      if (typeof cell.value === 'number') {
        return `<c r="${addr}"${s}><v>${cell.value}</v></c>`
      }
      return `<c r="${addr}" t="s"${s}><v>${stringIndex.get(cell.value)!}</v></c>`
    }).join('')
    return `<row r="${ri + 1}">${cells}</row>`
  }).join('')

  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    + '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    + (colsXml ? `<cols>${colsXml}</cols>` : '')
    + `<sheetData>${rowsXml}</sheetData>`
    + '</worksheet>'
}

// ── Minimal ZIP writer (Store = no compression) ───────────────────────────────

const TEXT_ENC = new TextEncoder()

const CRC32_TABLE = (() => {
  const t = new Uint32Array(256)
  for (let i = 0; i < 256; i++) {
    let c = i
    for (let j = 0; j < 8; j++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1
    t[i] = c
  }
  return t
})()

function crc32(data: Uint8Array): number {
  let crc = 0xFFFFFFFF
  for (let i = 0; i < data.length; i++) crc = CRC32_TABLE[(crc ^ data[i]) & 0xFF] ^ (crc >>> 8)
  return (crc ^ 0xFFFFFFFF) >>> 0
}

function u16(n: number): number[] { return [n & 0xFF, (n >> 8) & 0xFF] }
function u32(n: number): number[] {
  return [n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF, (n >> 24) & 0xFF]
}

function buildZip(files: Array<{ name: string; content: string }>): Blob {
  const localParts: number[][] = []
  const cdEntries: number[][] = []
  let offset = 0

  for (const { name, content } of files) {
    const nameBytes = Array.from(TEXT_ENC.encode(name))
    const data = TEXT_ENC.encode(content)
    const crc = crc32(data)
    const sz = data.length
    const dataArr = Array.from(data)

    const localHeader = [
      0x50, 0x4B, 0x03, 0x04,       // Local file header signature
      ...u16(20), ...u16(0), ...u16(0), // Version, flags, compression (Store)
      ...u16(0), ...u16(0),           // Mod time, mod date
      ...u32(crc), ...u32(sz), ...u32(sz),
      ...u16(nameBytes.length), ...u16(0), // Name length, extra length
      ...nameBytes,
    ]

    cdEntries.push([
      0x50, 0x4B, 0x01, 0x02,
      ...u16(20), ...u16(20), ...u16(0), ...u16(0),
      ...u16(0), ...u16(0),
      ...u32(crc), ...u32(sz), ...u32(sz),
      ...u16(nameBytes.length), ...u16(0), ...u16(0),
      ...u16(0), ...u16(0), ...u32(0), ...u32(offset),
      ...nameBytes,
    ])

    localParts.push([...localHeader, ...dataArr])
    offset += localHeader.length + sz
  }

  const cd = cdEntries.flat()
  const eocd = [
    0x50, 0x4B, 0x05, 0x06,
    ...u16(0), ...u16(0),
    ...u16(files.length), ...u16(files.length),
    ...u32(cd.length), ...u32(offset), ...u16(0),
  ]

  return new Blob([new Uint8Array([...localParts.flat(), ...cd, ...eocd])], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
}

// ── Core XLSX builder ─────────────────────────────────────────────────────────

function buildXlsx(rows: XlsxRow[], colWidths: number[], sheetName: string): Blob {
  const strings: string[] = []
  const stringIndex = new Map<string, number>()

  for (const row of rows) {
    for (const cell of row) {
      if (typeof cell.value === 'string' && cell.value !== '' && !stringIndex.has(cell.value)) {
        stringIndex.set(cell.value, strings.length)
        strings.push(cell.value)
      }
    }
  }

  return buildZip([
    { name: '[Content_Types].xml',        content: contentTypesXml() },
    { name: '_rels/.rels',                content: rootRelsXml() },
    { name: 'xl/workbook.xml',            content: workbookXml(sheetName) },
    { name: 'xl/_rels/workbook.xml.rels', content: workbookRelsXml() },
    { name: 'xl/styles.xml',              content: stylesXml() },
    { name: 'xl/sharedStrings.xml',       content: sharedStringsXml(strings) },
    { name: 'xl/worksheets/sheet1.xml',   content: worksheetXml(rows, colWidths, stringIndex) },
  ])
}

function triggerDownload(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  document.body.appendChild(a)
  a.click()
  setTimeout(() => { URL.revokeObjectURL(url); document.body.removeChild(a) }, 100)
}

// ── Matrix Export ─────────────────────────────────────────────────────────────

export async function exportMatrixToExcel(
  matrix: MatrixResponse,
  fromDt: string,
  toDt: string,
): Promise<void> {
  const headerRow: XlsxRow = [
    { value: 'Gemeinde', style: STYLE_HEADER_BLUE },
    ...matrix.dates.map((d): XlsxCell => {
      const isHoliday = (matrix.holidays[d]?.length ?? 0) > 0
      const label = isHoliday
        ? `${formatDate(d)} – ${matrix.holidays[d].join(', ')}`
        : formatDate(d)
      return { value: label, style: isHoliday ? STYLE_HEADER_AMBER : STYLE_HEADER_BLUE }
    }),
  ]

  const dataRows: XlsxRow[] = matrix.rows.map((row): XlsxRow => [
    { value: row.congregation_name, style: STYLE_BOLD },
    ...matrix.dates.map((d): XlsxCell => {
      const cell = row.cells[d]
      if (!cell?.event_id) return { value: '–' }
      if (cell.is_gap) return { value: 'LÜCKE', style: STYLE_GAP }
      const parts: string[] = []
      if (cell.event_title) parts.push(cell.event_title)
      if (cell.leader_name)  parts.push(cell.leader_name)
      return { value: parts.join(' / ') || '–' }
    }),
  ])

  const colWidths = [20, ...matrix.dates.map(() => 18)]
  triggerDownload(buildXlsx([headerRow, ...dataRows], colWidths, 'Dienstplan-Matrix'),
    `Dienstplan-Matrix_${fromDt}_${toDt}.xlsx`)
}

// ── Events Export ─────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<string, string> = {
  DRAFT: 'Entwurf', PUBLISHED: 'Veröffentlicht', CANCELLED: 'Abgesagt',
}
const SOURCE_LABELS: Record<string, string> = {
  INTERNAL: 'Intern', EXTERNAL: 'Extern',
}

export async function exportEventsToExcel(
  events: EventResponse[],
  fileName = 'Ereignisse.xlsx',
): Promise<void> {
  const headerRow: XlsxRow = [
    { value: 'Titel',     style: STYLE_HEADER_BLUE },
    { value: 'Beginn',    style: STYLE_HEADER_BLUE },
    { value: 'Ende',      style: STYLE_HEADER_BLUE },
    { value: 'Kategorie', style: STYLE_HEADER_BLUE },
    { value: 'Status',    style: STYLE_HEADER_BLUE },
    { value: 'Quelle',    style: STYLE_HEADER_BLUE },
  ]

  const dataRows: XlsxRow[] = events.map((e): XlsxRow => [
    { value: e.title },
    { value: formatDateTime(e.start_at) },
    { value: formatDateTime(e.end_at) },
    { value: e.category ?? '' },
    { value: STATUS_LABELS[e.status] ?? e.status },
    { value: SOURCE_LABELS[e.source] ?? e.source },
  ])

  triggerDownload(buildXlsx([headerRow, ...dataRows], [32, 18, 18, 18, 16, 12], 'Ereignisse'),
    fileName)
}
