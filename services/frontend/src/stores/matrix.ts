import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchMatrix, type MatrixResponse } from '../api/matrix'
import { parseConflictError } from '../api/errors'
import {
  createAssignment,
  deleteAssignment,
  type AssignmentOptions,
  updateAssignment,
} from '../api/serviceAssignments'
import { generateMatrixDraftServices } from '../api/districts'

export const useMatrixStore = defineStore('matrix', () => {
  const matrix = ref<MatrixResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Active filters
  const districtId = ref<string>('')
  const groupId = ref<string>('')
  const fromDt = ref<string>('')
  const toDt = ref<string>('')
  /** Client-side text filter on congregation names; not sent to the API. */
  const congregationQuery = ref<string>('')

  async function fetch() {
    if (!districtId.value || !fromDt.value || !toDt.value) return
    loading.value = true
    error.value = null
    try {
      matrix.value = await fetchMatrix(
        districtId.value,
        fromDt.value,
        toDt.value,
        groupId.value || undefined,
      )
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unbekannter Fehler'
    } finally {
      loading.value = false
    }
  }

  async function assign(
    eventId: string,
    assignmentId: string | null,
    options: AssignmentOptions,
    assignmentStatus?: 'OPEN' | 'ASSIGNED' | 'CONFIRMED',
  ) {
    try {
      if (assignmentId) {
        if (assignmentStatus) {
          await updateAssignment(eventId, assignmentId, options, assignmentStatus)
        } else {
          await updateAssignment(eventId, assignmentId, options)
        }
      } else {
        await createAssignment(eventId, options, assignmentStatus ?? 'ASSIGNED')
      }
    } catch (e) {
      const conflictError = parseConflictError(e)
      if (conflictError) {
        throw conflictError
      }
      throw e
    }
    await fetch() // refresh matrix
  }

  async function clearAssignment(eventId: string, assignmentId: string | null) {
    if (!assignmentId) {
      await fetch()
      return
    }

    await deleteAssignment(eventId, assignmentId)
    await fetch()
  }

  async function generateDraftsForCurrentRange() {
    if (!districtId.value || !fromDt.value || !toDt.value) {
      throw new Error('Bezirk und Zeitraum sind erforderlich')
    }
    const result = await generateMatrixDraftServices(districtId.value, fromDt.value, toDt.value)
    await fetch()
    return result
  }

  return {
    matrix,
    loading,
    error,
    districtId,
    groupId,
    fromDt,
    toDt,
    congregationQuery,
    fetch,
    assign,
    clearAssignment,
    generateDraftsForCurrentRange,
  }
})
