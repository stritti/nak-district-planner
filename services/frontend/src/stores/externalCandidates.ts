// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

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
  const loadError = ref<string | null>(null)
  const reviewError = ref<string | null>(null)
  let fetchSequence = 0

  async function fetchPending(districtId: string) {
    const requestSequence = ++fetchSequence
    loading.value = true
    loadError.value = null
    try {
      const candidates = await listExternalCandidates(districtId)
      if (requestSequence === fetchSequence) {
        items.value = candidates
      }
    } catch (cause) {
      if (requestSequence === fetchSequence) {
        loadError.value = cause instanceof Error ? cause.message : 'Kandidaten konnten nicht geladen werden'
      }
    } finally {
      if (requestSequence === fetchSequence) {
        loading.value = false
      }
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
    reviewError.value = null
    try {
      const updated = await action()
      items.value = items.value.filter((item) => item.id !== updated.id)
      return updated
    } catch (cause) {
      reviewError.value = cause instanceof Error ? cause.message : 'Prüfung konnte nicht gespeichert werden'
      return null
    } finally {
      reviewingId.value = null
    }
  }

  return {
    items,
    loading,
    reviewingId,
    loadError,
    reviewError,
    fetchPending,
    acceptAndCreate,
    dismiss,
  }
})
