// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { parseConflictError } from '../api/errors'
import { useConfirm } from './useConfirm'

export interface WarnConflictDialog {
  title: string
  confirmText: string
  abortMessage: string
}

export function useWarnConflictRetry() {
  const confirm = useConfirm()

  return async function runWithWarnRetry<T>(
    attempt: (acknowledged: boolean) => Promise<T>,
    dialog: WarnConflictDialog,
  ): Promise<T> {
    try {
      return await attempt(false)
    } catch (cause) {
      const conflict = parseConflictError(cause)
      if (!conflict || conflict.blocking.length || !conflict.warnings.length) throw cause
      const confirmed = await confirm({
        title: dialog.title,
        message: conflict.warnings.map((warning) => warning.message).join(' '),
        confirmText: dialog.confirmText,
        variant: 'warning',
      })
      if (!confirmed) throw new Error(dialog.abortMessage)
      return attempt(true)
    }
  }
}
