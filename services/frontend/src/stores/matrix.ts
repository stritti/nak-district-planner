import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchMatrix, type MatrixResponse } from '../api/matrix'
import { createAssignment, updateAssignment } from '../api/serviceAssignments'
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
    options: { leaderId?: string | null; leaderName?: string | null },
  ) {
    if (assignmentId) {
      await updateAssignment(eventId, assignmentId, options, 'ASSIGNED')
    } else {
      await createAssignment(eventId, options, 'ASSIGNED')
    }
    await fetch() // refresh matrix
  }

  async function clearAssignment(eventId: string, assignmentId: string | null) {
    if (!assignmentId) {
      await fetch()
      return
    }

    await updateAssignment(
      eventId,
      assignmentId,
      { leaderId: null, leaderName: null },
      'OPEN',
    )
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
    fetch,
    assign,
    clearAssignment,
    generateDraftsForCurrentRange,
  }
}, {
  persist: { pick: ['districtId', 'groupId', 'fromDt', 'toDt'] },
})
