// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { parseConflictError } from '../api/errors'
import { changeAssignmentInline, type InlineAssignmentResult } from '../api/serviceAssignments'
import { useConfirm } from './useConfirm'

/** Shared conditional write: acknowledge WARN only, retry once with the same snapshot. */
export function useInlineAssignmentSave() {
  const confirm = useConfirm()

  return async function saveInlineAssignment(
    eventId: string,
    leaderId: string,
    revision: string,
  ): Promise<InlineAssignmentResult> {
    try {
      return await changeAssignmentInline(eventId, leaderId, revision)
    } catch (cause) {
      const conflict = parseConflictError(cause)
      if (!conflict || conflict.blocking.length || !conflict.warnings.length) throw cause
      const confirmed = await confirm({
        title: 'Konflikt bei der Zuordnung',
        message: conflict.warnings.map((warning) => warning.message).join(' '),
        confirmText: 'Trotzdem zuordnen',
        variant: 'warning',
      })
      if (!confirmed) throw new Error('Zuordnung abgebrochen')
      return changeAssignmentInline(eventId, leaderId, revision, true)
    }
  }
}
