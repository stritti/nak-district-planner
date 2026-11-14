// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { changeAssignmentInline, type InlineAssignmentResult } from '../api/serviceAssignments'
import { useWarnConflictRetry } from './useWarnConflictRetry'

/**
 * Acknowledge WARN only and retry once with the original snapshot.
 * A 409/412 (or any other failure) on that confirmed retry propagates to the
 * cell unchanged; it never opens another prompt or starts a retry loop.
 */
export function useInlineAssignmentSave() {
  const retryOnWarnings = useWarnConflictRetry()

  return async function saveInlineAssignment(
    eventId: string,
    leaderId: string,
    revision: string,
  ): Promise<InlineAssignmentResult> {
    return retryOnWarnings(
      (acknowledged) =>
        acknowledged
          ? changeAssignmentInline(eventId, leaderId, revision, true)
          : changeAssignmentInline(eventId, leaderId, revision),
      {
        title: 'Konflikt bei der Zuordnung',
        confirmText: 'Trotzdem zuordnen',
        abortMessage: 'Zuordnung abgebrochen',
      },
    )
  }
}
