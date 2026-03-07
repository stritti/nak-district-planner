import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchMatrix, type MatrixResponse } from '@/api/matrix'
import { createAssignment } from '@/api/serviceAssignments'

export const useMatrixStore = defineStore('matrix', () => {
  const matrix = ref<MatrixResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Active filters
  const districtId = ref<string>('')
  const fromDt = ref<string>('')
  const toDt = ref<string>('')

  async function fetch() {
    if (!districtId.value || !fromDt.value || !toDt.value) return
    loading.value = true
    error.value = null
    try {
      matrix.value = await fetchMatrix(districtId.value, fromDt.value, toDt.value)
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unbekannter Fehler'
    } finally {
      loading.value = false
    }
  }

  async function assign(eventId: string, leaderName: string) {
    await createAssignment(eventId, leaderName, 'ASSIGNED')
    await fetch() // refresh matrix
  }

  return { matrix, loading, error, districtId, fromDt, toDt, fetch, assign }
}, {
  persist: { pick: ['districtId', 'fromDt', 'toDt'] },
})
