// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { parseConflictError } from '../api/errors'
import { updateEvent, type EventResponse } from '../api/events'
import { useConfirm } from './useConfirm'

const pad = (value: number) => String(value).padStart(2, '0')

/** `YYYY-MM-DDTHH:mm` in the viewer's local time, as `datetime-local` inputs expect. */
export function toLocalInputValue(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/**
 * Inline start-time change. Start and end move together so the duration is kept.
 * The server revalidates minister assignments atomically; only WARN-level
 * conflicts can be acknowledged (once, explicitly). BLOCK, 412 and every other
 * failure propagate to the cell unchanged, never as a blind retry.
 */
export function useInlineScheduleSave() {
  const confirm = useConfirm()

  return async function saveInlineSchedule(
    event: EventResponse,
    draft: string,
    revision: string,
  ): Promise<EventResponse> {
    const start = new Date(draft)
    if (Number.isNaN(start.getTime())) throw new Error('Ungültiges Datum')
    const duration = Math.max(new Date(event.end_at).getTime() - new Date(event.start_at).getTime(), 0)
    const payload = {
      start_at: start.toISOString(),
      end_at: new Date(start.getTime() + duration).toISOString(),
    }
    try {
      return await updateEvent(event.id, payload, revision)
    } catch (cause) {
      const conflict = parseConflictError(cause)
      if (!conflict || conflict.blocking.length || !conflict.warnings.length) throw cause
      const confirmed = await confirm({
        title: 'Konflikt bei der Terminänderung',
        message: conflict.warnings.map((warning) => warning.message).join(' '),
        confirmText: 'Trotzdem ändern',
        variant: 'warning',
      })
      if (!confirmed) throw new Error('Änderung abgebrochen')
      return updateEvent(event.id, { ...payload, confirm_warnings: true }, revision)
    }
  }
}
