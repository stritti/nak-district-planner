// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchMatrix, type MatrixResponse } from '../api/matrix'
import { parseConflictError, userMessage } from '../api/errors'
import {
  createAssignment,
  deleteAssignment,
  type AssignmentOptions,
  type InlineAssignmentResult,
  updateAssignment,
} from '../api/serviceAssignments'
import { useLeadersStore } from './leaders'
import { generateMatrixDraftServices } from '../api/districts'

export const useMatrixStore = defineStore('matrix', () => {
  const matrix = ref<MatrixResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const conflictsStale = ref(false)
  const conflictsRefreshError = ref<string | null>(null)
  // Discard refresh responses that predate a newer inline write or a full reload.
  let conflictRevision = 0

  // Active filters
  const districtId = ref<string>('')
  const groupId = ref<string>('')
  const fromDt = ref<string>('')
  const toDt = ref<string>('')
  /** Client-side text filter on congregation names; not sent to the API. */
  const congregationQuery = ref<string>('')

  async function fetch() {
    if (!districtId.value || !fromDt.value || !toDt.value) return
    loading.value = true
    error.value = null
    try {
      matrix.value = await fetchMatrix(
        districtId.value,
        fromDt.value,
        toDt.value,
        groupId.value || undefined,
      )
      conflictRevision++
      conflictsStale.value = false
      conflictsRefreshError.value = null
    } catch (e) {
      error.value = userMessage(e, 'Unbekannter Fehler')
    } finally {
      loading.value = false
    }
  }

  /** Apply the saved assignment without remounting the editing cell. */
  function applyInlineAssignment(eventId: string, saved: InlineAssignmentResult) {
    const leaders = useLeadersStore()
    const label = saved.leader_name ?? (
      leaders.districtId === districtId.value ? leaders.labelFor(saved.leader_id) : null
    )
    for (const row of matrix.value?.rows ?? []) {
      for (const cell of Object.values(row.cells)) {
        if ((cell.assignment_event_id ?? cell.event_id) === eventId) {
          Object.assign(cell, {
            assignment_id: saved.id,
            assignment_status: saved.status,
            leader_id: saved.leader_id,
            leader_name: label,
            revision: saved.event_revision,
            is_gap: false,
          })
        }
        // Any assignment may affect other leaders' conflicts in the date range.
        // Do not keep displaying stale warnings while the refresh is in flight.
        cell.conflicts = []
      }
    }
    conflictRevision++
    conflictsStale.value = true
    conflictsRefreshError.value = null
  }

  /** Refresh conflict markers in place, preserving inline editor focus and saved state. */
  async function refreshConflicts() {
    if (!matrix.value || !districtId.value || !fromDt.value || !toDt.value) {
      conflictsRefreshError.value = 'Konfliktprüfung nicht verfügbar. Matrix neu laden.'
      return
    }
    const revision = conflictRevision
    const [district, from, to, group] = [
      districtId.value, fromDt.value, toDt.value, groupId.value,
    ]
    try {
      const latest = await fetchMatrix(district, from, to, group || undefined)
      if (revision !== conflictRevision ||
          district !== districtId.value || from !== fromDt.value ||
          to !== toDt.value || group !== groupId.value) return

      const latestRows = new Map(latest.rows.map((row) => [row.congregation_id, row]))
      for (const row of matrix.value.rows) {
        const newCells = latestRows.get(row.congregation_id)?.cells
        for (const [date, cell] of Object.entries(row.cells)) {
          cell.conflicts = newCells?.[date]?.conflicts ?? []
          cell.service_count = newCells?.[date]?.service_count
        }
      }
      conflictsStale.value = false
      conflictsRefreshError.value = null
    } catch {
      if (revision === conflictRevision) {
        conflictsRefreshError.value =
          'Zuordnung gespeichert, aber Konflikte konnten nicht aktualisiert werden. Matrix neu laden.'
      }
    }
  }

  async function assign(
    eventId: string,
    assignmentId: string | null,
    options: AssignmentOptions,
    assignmentStatus: 'OPEN' | 'ASSIGNED' | 'CONFIRMED' | undefined,
    revision: string,
  ) {
    try {
      if (assignmentId) {
        await updateAssignment(eventId, assignmentId, options, revision, assignmentStatus)
      } else {
        await createAssignment(eventId, options, revision, assignmentStatus ?? 'ASSIGNED')
      }
    } catch (e) {
      const conflictError = parseConflictError(e)
      if (conflictError) {
        throw conflictError
      }
      throw e
    }
    await fetch() // refresh matrix
  }

  async function clearAssignment(eventId: string, assignmentId: string | null, revision: string) {
    if (!assignmentId) {
      await fetch()
      return
    }

    await deleteAssignment(eventId, assignmentId, revision)
    await fetch()
  }

  async function generateDraftsForCurrentRange() {
    if (!districtId.value || !fromDt.value || !toDt.value) {
      throw new Error('Bezirk und Zeitraum sind erforderlich')
    }
    const result = await generateMatrixDraftServices(districtId.value, fromDt.value, toDt.value)
    await fetch()
    return result
  }

  return {
    matrix,
    loading,
    error,
    conflictsStale,
    conflictsRefreshError,
    districtId,
    groupId,
    fromDt,
    toDt,
    congregationQuery,
    fetch,
    applyInlineAssignment,
    refreshConflicts,
    assign,
    clearAssignment,
    generateDraftsForCurrentRange,
  }
})
