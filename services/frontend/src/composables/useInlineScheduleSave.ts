// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { updateEvent, type EventResponse } from '../api/events'
import { useWarnConflictRetry } from './useWarnConflictRetry'

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
  const retryOnWarnings = useWarnConflictRetry()

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
    return retryOnWarnings(
      (acknowledged) =>
        updateEvent(event.id, acknowledged ? { ...payload, confirm_warnings: true } : payload, revision),
      {
        title: 'Konflikt bei der Terminänderung',
        confirmText: 'Trotzdem ändern',
        abortMessage: 'Änderung abgebrochen',
      },
    )
  }
}
