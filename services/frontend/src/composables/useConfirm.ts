// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { shallowRef } from 'vue'
import { useConfirmDialog } from '@vueuse/core'

export interface ConfirmOptions {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'warning' | 'info'
  /** Require typing a confirmation word (irreversible actions). */
  dangerous?: boolean
}

// One application-wide dialog rendered by <ConfirmHost /> in App.vue. Created
// lazily so that importing this module has no side effects.
const options = shallowRef<ConfirmOptions | null>(null)
let sharedDialog: ReturnType<typeof useConfirmDialog> | undefined

function dialogState() {
  sharedDialog ??= useConfirmDialog()
  return sharedDialog
}

/**
 * Ask the user for confirmation.
 *
 * ```ts
 * const confirm = useConfirm()
 * if (!(await confirm({ title: 'Absagen?', message: '…', variant: 'warning' }))) return
 * ```
 *
 * Resolves `true` on confirm and `false` on cancel. A new request while a
 * dialog is open cancels the pending one, so callers never wait forever.
 */
export function useConfirm() {
  return async function confirm(request: ConfirmOptions): Promise<boolean> {
    const dialog = dialogState()
    if (dialog.isRevealed.value) dialog.cancel()
    options.value = request
    const { isCanceled } = await dialog.reveal()
    return !isCanceled
  }
}

/** State and actions for the single dialog host component. */
export function useConfirmHost() {
  const dialog = dialogState()
  return {
    options,
    isRevealed: dialog.isRevealed,
    confirm: () => dialog.confirm(),
    cancel: () => dialog.cancel(),
  }
}
