import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ConflictItem } from '../api/errors'

/**
 * Holds conflict state for the currently open assignment dialog.
 * The banner and submit logic read from here so conflict handling
 * stays consistent across matrix and dialog components.
 */
export const useConflictStore = defineStore('conflict', () => {
  const conflicts = ref<ConflictItem[]>([])
  const confirmingWarning = ref(false)

  const blocking = ref<ConflictItem[]>([])
  const warnings = ref<ConflictItem[]>([])

  function setConflicts(items: ConflictItem[]) {
    conflicts.value = items
    blocking.value = items.filter((c) => c.severity === 'BLOCK')
    warnings.value = items.filter((c) => c.severity === 'WARN')
  }

  function clear() {
    conflicts.value = []
    blocking.value = []
    warnings.value = []
    confirmingWarning.value = false
  }

  function beginWarnConfirmation() {
    confirmingWarning.value = true
  }

  function cancelWarnConfirmation() {
    confirmingWarning.value = false
  }

  return {
    conflicts,
    blocking,
    warnings,
    confirmingWarning,
    setConflicts,
    clear,
    beginWarnConfirmation,
    cancelWarnConfirmation,
  }
})
