// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { NotificationItem } from '../api/notifications'

/** Allow only known internal destinations; never navigate to untrusted payload URLs. */
export function notificationDestination(
  notification: Pick<NotificationItem, 'type' | 'payload'>,
): string | null {
  const payload = notification.payload
  const candidateId = payload.candidate_id ?? payload.reference_id
  if (
    (notification.type === 'EXTERNAL_EVENT_DETECTED' || notification.type === 'CANDIDATE_REVIEW') &&
    typeof candidateId === 'string' &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(candidateId)
  ) {
    return `/admin/external-candidates?candidate_id=${encodeURIComponent(candidateId)}`
  }
  return null
}
