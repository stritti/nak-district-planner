// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { ref, type Ref } from 'vue'

import { userMessage } from '../api/errors'
import { useToastStore } from '../stores/toast'

export interface CrudDeleteOptions<T> {
  deleteItem: (item: T) => Promise<unknown>
  onDeleted?: (item: T) => void
  label: (item: T) => string
  successMessage: string
  errorMessage?: string
}

export function useCrudDelete<T>(options: CrudDeleteOptions<T>, busy?: Ref<boolean>) {
  const toastStore = useToastStore()
  const deleteTarget: Ref<T | null> = ref(null)
  const deleting = busy ?? ref(false)

  function confirmDelete(item: T): void {
    deleteTarget.value = item
  }

  async function executeDelete(): Promise<void> {
    if (!deleteTarget.value) return
    const target = deleteTarget.value
    deleting.value = true
    try {
      await options.deleteItem(target)
      options.onDeleted?.(target)
      deleteTarget.value = null
      toastStore.success(options.successMessage, options.label(target))
    } catch (e) {
      toastStore.error(options.errorMessage ?? 'Löschen fehlgeschlagen', userMessage(e, 'Unbekannter Fehler'))
    } finally {
      deleting.value = false
    }
  }

  return { deleteTarget, deleting, confirmDelete, executeDelete }
}
