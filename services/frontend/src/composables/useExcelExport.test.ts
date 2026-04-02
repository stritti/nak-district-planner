import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { exportMatrixToExcel, exportEventsToExcel } from './useExcelExport'
import type { MatrixResponse } from '@/api/matrix'
import type { EventResponse } from '@/api/events'

// Mock DOM API
const mockClick = vi.fn()
const mockRemoveChild = vi.fn()

beforeEach(() => {
  // Use fake timers to handle setTimeout
  vi.useFakeTimers()

  // Mock document.createElement and URL.createObjectURL/revokeObjectURL
  document.createElement = vi.fn((tag: string) => {
    if (tag === 'a') {
      return {
        href: '',
        download: '',
        click: mockClick,
      } as unknown as HTMLElement
    }
    return document.createElement(tag)
  })

  document.body.appendChild = vi.fn()
  document.body.removeChild = mockRemoveChild

  URL.createObjectURL = vi.fn(() => 'blob:mock-url')
  URL.revokeObjectURL = vi.fn()
})

afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
})

describe('useExcelExport', () => {
  describe('exportMatrixToExcel', () => {
    it('should export matrix data as XLSX', async () => {
      const matrix: MatrixResponse = {
        dates: ['2024-01-01', '2024-01-08'],
        rows: [
          {
            congregation_id: 'cong1',
            congregation_name: 'Gemeinde A',
            cells: {
              '2024-01-01': {
                event_id: 'evt1',
                event_title: 'Gottesdienst',
                category: 'Gottesdienst',
                leader_name: 'Max Mustermann',
                leader_id: 'ldr1',
                is_gap: false,
                assignment_id: 'asg1',
                assignment_status: 'CONFIRMED',
              },
              '2024-01-08': {
                event_id: 'evt2',
                event_title: 'Gottesdienst',
                category: 'Gottesdienst',
                leader_name: null,
                leader_id: null,
                is_gap: true,
                assignment_id: null,
                assignment_status: null,
              },
            },
          },
        ],
        holidays: {
          '2024-01-01': ['Neujahrstag'],
        },
      }

      await exportMatrixToExcel(matrix, '2024-01-01', '2024-01-31')

      expect(mockClick).toHaveBeenCalled()
      expect(URL.createObjectURL).toHaveBeenCalled()

      // Advance timers to handle setTimeout cleanup
      vi.runAllTimers()

      expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mock-url')
    })

    it('should include holiday information in headers', async () => {
      const matrix: MatrixResponse = {
        dates: ['2024-01-01'],
        rows: [
          {
            congregation_id: 'cong1',
            congregation_name: 'Gemeinde A',
            cells: {
              '2024-01-01': {
                event_id: 'evt1',
                event_title: 'Service',
                category: 'Service',
                leader_name: 'John Doe',
                leader_id: 'ldr1',
                is_gap: false,
                assignment_id: 'asg1',
                assignment_status: 'ASSIGNED',
              },
            },
          },
        ],
        holidays: {
          '2024-01-01': ['Neujahrstag', 'Feiertag'],
        },
      }

      await exportMatrixToExcel(matrix, '2024-01-01', '2024-01-31')

      expect(mockClick).toHaveBeenCalled()
    })

    it('should handle empty matrix', async () => {
      const matrix: MatrixResponse = {
        dates: [],
        rows: [],
        holidays: {},
      }

      await exportMatrixToExcel(matrix, '2024-01-01', '2024-01-31')

      expect(mockClick).toHaveBeenCalled()
    })
  })

  describe('exportEventsToExcel', () => {
    it('should export events as XLSX', async () => {
      const events: EventResponse[] = [
        {
          id: 'evt1',
          district_id: 'dist1',
          title: 'Gottesdienst',
          description: 'Sunday Service',
          category: 'Gottesdienst',
          start_at: '2024-01-01T10:00:00Z',
          end_at: '2024-01-01T11:00:00Z',
          status: 'PUBLISHED',
          source: 'INTERNAL',
          visibility: 'PUBLIC',
          congregation_id: null,
          audiences: [],
          applicability: [],
          created_at: '2023-12-01T08:00:00Z',
          updated_at: '2023-12-01T08:00:00Z',
        },
        {
          id: 'evt2',
          district_id: 'dist1',
          title: 'Bibelstudie',
          description: 'Bible Study',
          category: 'Bibelstudie',
          start_at: '2024-01-02T19:00:00Z',
          end_at: '2024-01-02T20:30:00Z',
          status: 'DRAFT',
          source: 'EXTERNAL',
          visibility: 'INTERNAL',
          congregation_id: null,
          audiences: [],
          applicability: [],
          created_at: '2023-12-01T08:00:00Z',
          updated_at: '2023-12-01T08:00:00Z',
        },
      ]

      await exportEventsToExcel(events)

      expect(mockClick).toHaveBeenCalled()
      expect(URL.createObjectURL).toHaveBeenCalled()
    })

    it('should include all event statuses', async () => {
      const events: EventResponse[] = [
        {
          id: 'evt1',
          district_id: 'dist1',
          title: 'Draft Event',
          description: '',
          category: 'Service',
          start_at: '2024-01-01T10:00:00Z',
          end_at: '2024-01-01T11:00:00Z',
          status: 'DRAFT',
          source: 'INTERNAL',
          visibility: 'INTERNAL',
          congregation_id: null,
          audiences: [],
          applicability: [],
          created_at: '2023-12-01T08:00:00Z',
          updated_at: '2023-12-01T08:00:00Z',
        },
        {
          id: 'evt2',
          district_id: 'dist1',
          title: 'Published Event',
          description: '',
          category: 'Service',
          start_at: '2024-01-02T10:00:00Z',
          end_at: '2024-01-02T11:00:00Z',
          status: 'PUBLISHED',
          source: 'INTERNAL',
          visibility: 'PUBLIC',
          congregation_id: null,
          audiences: [],
          applicability: [],
          created_at: '2023-12-01T08:00:00Z',
          updated_at: '2023-12-01T08:00:00Z',
        },
        {
          id: 'evt3',
          district_id: 'dist1',
          title: 'Cancelled Event',
          description: '',
          category: 'Service',
          start_at: '2024-01-03T10:00:00Z',
          end_at: '2024-01-03T11:00:00Z',
          status: 'CANCELLED',
          source: 'INTERNAL',
          visibility: 'INTERNAL',
          congregation_id: null,
          audiences: [],
          applicability: [],
          created_at: '2023-12-01T08:00:00Z',
          updated_at: '2023-12-01T08:00:00Z',
        },
      ]

      await exportEventsToExcel(events)

      expect(mockClick).toHaveBeenCalled()
    })

    it('should handle empty events list', async () => {
      await exportEventsToExcel([])

      expect(mockClick).toHaveBeenCalled()
    })

    it('should use custom filename', async () => {
      const events: EventResponse[] = [
        {
          id: 'evt1',
          district_id: 'dist1',
          title: 'Event',
          description: '',
          category: 'Service',
          start_at: '2024-01-01T10:00:00Z',
          end_at: '2024-01-01T11:00:00Z',
          status: 'PUBLISHED',
          source: 'INTERNAL',
          visibility: 'PUBLIC',
          congregation_id: null,
          audiences: [],
          applicability: [],
          created_at: '2023-12-01T08:00:00Z',
          updated_at: '2023-12-01T08:00:00Z',
        },
      ]

      await exportEventsToExcel(events, 'custom-filename.xlsx')

      expect(mockClick).toHaveBeenCalled()
    })
  })

  describe('XLSX generation', () => {
    it('should generate valid ZIP structure', async () => {
      const matrix: MatrixResponse = {
        dates: ['2024-01-01'],
        rows: [
          {
            congregation_id: 'cong1',
            congregation_name: 'Gemeinde A',
            cells: {
              '2024-01-01': {
                event_id: 'evt1',
                event_title: 'Service',
                category: 'Service',
                leader_name: 'Leader Name',
                leader_id: 'ldr1',
                is_gap: false,
                assignment_id: 'asg1',
                assignment_status: 'ASSIGNED',
              },
            },
          },
        ],
        holidays: {},
      }

      await exportMatrixToExcel(matrix, '2024-01-01', '2024-01-31')

      // Verify Blob was created with correct mime type
      const createObjectURLCall = (URL.createObjectURL as unknown as { mock: { calls: Array<Array<unknown>> } }).mock.calls[0]
      expect(createObjectURLCall[0]).toBeInstanceOf(Blob)
      expect((createObjectURLCall[0] as Blob).type).toBe('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    })

    it('should properly escape XML special characters', async () => {
      const events: EventResponse[] = [
        {
          id: 'evt1',
          district_id: 'dist1',
          title: 'Event with <XML> & "quotes"',
          description: 'Test',
          category: 'Service',
          start_at: '2024-01-01T10:00:00Z',
          end_at: '2024-01-01T11:00:00Z',
          status: 'PUBLISHED',
          source: 'INTERNAL',
          visibility: 'PUBLIC',
          congregation_id: null,
          audiences: [],
          applicability: [],
          created_at: '2023-12-01T08:00:00Z',
          updated_at: '2023-12-01T08:00:00Z',
        },
      ]

      await exportEventsToExcel(events)

      expect(mockClick).toHaveBeenCalled()
    })
  })
})
