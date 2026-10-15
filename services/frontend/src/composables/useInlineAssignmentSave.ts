// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { parseConflictError } from '../api/errors'
import { changeAssignmentInline, type InlineAssignmentResult } from '../api/serviceAssignments'
import { useConfirm } from './useConfirm'

/**
 * Acknowledge WARN only and retry once with the original snapshot.
 * A 409/412 (or any other failure) on that confirmed retry propagates to the
 * cell unchanged; it never opens another prompt or starts a retry loop.
 */
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
