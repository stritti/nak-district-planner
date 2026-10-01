import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { ConflictItem } from '../api/errors'

export type PendingConflictAction = 'save' | 'confirm'

/**
 * Holds conflict state for the currently open assignment dialog.
 * The banner and submit logic read from here so conflict handling
 * stays consistent across matrix and dialog components.
 */
export const useConflictStore = defineStore('conflict', () => {
  const conflicts = ref<ConflictItem[]>([])
  const pendingAction = ref<PendingConflictAction | null>(null)

  const blocking = computed(() =>
    conflicts.value.filter((c) => c.severity !== 'WARN' && c.severity !== 'PASS'),
  )
  const warnings = computed(() => conflicts.value.filter((c) => c.severity === 'WARN'))
  const confirmingWarning = computed(() => pendingAction.value !== null)

  function setConflicts(items: ConflictItem[]) {
    conflicts.value = items
  }

  function beginWarnConfirmation(action: PendingConflictAction) {
    pendingAction.value = action
  }

  function cancelWarnConfirmation() {
    pendingAction.value = null
  }

  function clear() {
    conflicts.value = []
    pendingAction.value = null
  }

  return {
    conflicts,
    blocking,
    warnings,
    confirmingWarning,
    pendingAction,
    setConflicts,
    beginWarnConfirmation,
    cancelWarnConfirmation,
    clear,
  }
})
