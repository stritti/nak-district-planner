import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  acceptExternalCandidate,
  dismissExternalCandidate,
  listExternalCandidates,
  type ExternalEventCandidate,
} from '../api/externalCandidates'

export const useExternalCandidatesStore = defineStore('externalCandidates', () => {
  const items = ref<ExternalEventCandidate[]>([])
  const loading = ref(false)
  const reviewingId = ref<string | null>(null)
  const error = ref<string | null>(null)

  async function fetchPending(districtId: string) {
    loading.value = true
    error.value = null
    try {
      items.value = await listExternalCandidates(districtId)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : 'Kandidaten konnten nicht geladen werden'
    } finally {
      loading.value = false
    }
  }

  async function acceptAndCreate(candidateId: string) {
    return review(candidateId, () => acceptExternalCandidate(candidateId))
  }

  async function dismiss(candidateId: string) {
    return review(candidateId, () => dismissExternalCandidate(candidateId))
  }

  async function review(candidateId: string, action: () => Promise<ExternalEventCandidate>) {
    reviewingId.value = candidateId
    error.value = null
    try {
      const updated = await action()
      items.value = items.value.filter((item) => item.id !== updated.id)
      return updated
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : 'Prüfung konnte nicht gespeichert werden'
      return null
    } finally {
      reviewingId.value = null
    }
  }

  return { items, loading, reviewingId, error, fetchPending, acceptAndCreate, dismiss }
})
