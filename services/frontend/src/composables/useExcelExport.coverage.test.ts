import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { exportEventsToExcel } from './useExcelExport'

const originalCreateElement = document.createElement.bind(document)

beforeEach(() => {
  vi.useFakeTimers()
  const anchor = originalCreateElement('a')
  vi.spyOn(anchor, 'click').mockImplementation(() => undefined)
  vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => (
    tagName === 'a' ? anchor : originalCreateElement(tagName)
  ))
  vi.spyOn(document.body, 'appendChild').mockImplementation((node) => node)
  vi.spyOn(document.body, 'removeChild').mockImplementation((node) => node)
  vi.stubGlobal('URL', {
    ...URL,
    createObjectURL: vi.fn(() => 'blob:coverage'),
    revokeObjectURL: vi.fn(),
  })
})

afterEach(() => {
  vi.runAllTimers()
  vi.useRealTimers()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('useExcelExport coverage gaps', () => {
  it('serializes numeric and empty worksheet cells', async () => {
    const baseEvent = {
      id: 'evt-1',
      district_id: 'd1',
      description: '',
      category: 'Service',
      start_at: '2026-10-06T10:00:00Z',
      end_at: '2026-10-06T11:00:00Z',
      status: 'ACTIVE',
      source: 'INTERNAL',
      visibility: 'PUBLIC',
      congregation_id: null,
      applicability: [],
      created_at: '2026-10-01T00:00:00Z',
      updated_at: '2026-10-01T00:00:00Z',
    }

    await exportEventsToExcel([
      { ...baseEvent, title: 42 },
      { ...baseEvent, id: 'evt-2', title: null },
    ] as never)

    expect(URL.createObjectURL).toHaveBeenCalledTimes(1)
  })
})
