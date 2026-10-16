// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import {
  previewEventChange,
  updateEvent,
  type EventChangeImpact,
  type EventChangeImpactRequest,
  type EventResponse,
  type EventUpdate,
} from '../api/events'
import { useConfirm } from './useConfirm'

/**
 * Inline category / congregation changes.
 *
 * Both change which duties stay valid for a slot. The server never deletes them
 * (they are flagged for review or hidden from the new scope), but the user must
 * see that before committing. So every change runs the read-only impact preview
 * first with the cell's revision: BLOCK refuses, anything that flags duties or
 * raises a WARN needs one explicit confirmation, a clean preview patches directly.
 */
export function useInlineScopeSave() {
  const confirm = useConfirm()

  async function applyChange(
    event: EventResponse,
    revision: string,
    change: EventChangeImpactRequest & EventUpdate,
  ): Promise<EventResponse> {
    const impact = await previewEventChange(event.id, change, revision)
    if (impact.blocked) throw new Error(conflictMessages(impact, 'BLOCK') || 'Änderung nicht möglich.')

    const needsConfirmation = impact.requires_confirmation
      || impact.duties_newly_flagged > 0
      || impact.duties_newly_quarantined > 0
    if (needsConfirmation) {
      const confirmed = await confirm({
        title: 'Auswirkungen der Änderung',
        message: confirmationMessage(impact),
        confirmText: 'Trotzdem ändern',
        variant: 'warning',
      })
      if (!confirmed) throw new Error('Änderung abgebrochen')
    }
    // The server recomputes the duty impact under the slot lock; it only accepts what was shown here.
    return updateEvent(
      event.id,
      {
        ...change,
        ...(impact.requires_confirmation ? { confirm_warnings: true } : {}),
        acknowledged_duty_impact: {
          newly_flagged: impact.duties_newly_flagged,
          newly_quarantined: impact.duties_newly_quarantined,
        },
      },
      revision,
    )
  }

  async function saveCategory(event: EventResponse, draft: string, revision: string): Promise<EventResponse> {
    const category = draft.trim() || null
    if (category === (event.category ?? null)) return event
    return applyChange(event, revision, { category })
  }

  function saveCongregation(event: EventResponse, congregationId: string, revision: string): Promise<EventResponse> {
    return applyChange(event, revision, { congregation_id: congregationId || null })
  }

  return { saveCategory, saveCongregation }
}

function conflictMessages(impact: EventChangeImpact, severity: string): string {
  return impact.items
    .flatMap((item) => item.conflicts)
    .filter((conflict) => conflict.severity === severity)
    .map((conflict) => conflict.message)
    .join(' ')
}

function confirmationMessage(impact: EventChangeImpact): string {
  const parts: string[] = []
  const warnings = conflictMessages(impact, 'WARN')
  if (warnings) parts.push(warnings)
  if (impact.duties_newly_flagged > 0) {
    parts.push(
      `${impact.duties_newly_flagged} Dienst(e) werden zur Prüfung markiert und bleiben gespeichert.`,
    )
  }
  if (impact.duties_newly_quarantined > 0) {
    parts.push(
      `${impact.duties_newly_quarantined} Dienst(e) werden in der neuen Gemeinde ausgeblendet, bis sie neu bestätigt werden.`,
    )
  }
  return parts.join(' ')
}
