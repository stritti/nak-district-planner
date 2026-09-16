<template>
  <!-- Assignment Modal -->
  <div
    v-if="modal.open"
    class="modal-backdrop"
    @click.self="closeModal"
  >
    <div class="modal-panel max-w-md">
      <div class="flex items-center justify-between mb-1">
        <h2 class="modal-title">
          {{ modal.isGap ? 'Amtstragende:n zuweisen' : 'Zuweisung bearbeiten' }}
        </h2>
        <button class="modal-close" @click="closeModal">
          <XMarkIcon class="h-5 w-5" />
        </button>
      </div>
      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        {{ modal.congregationName }} — {{ formatDate(modal.date) }}
      </p>
      <p class="text-sm text-gray-700 dark:text-gray-300 mb-4">
        <span class="font-medium">Ereignis:</span> {{ modal.eventTitle }}
      </p>

      <div class="mb-4 rounded border border-gray-200 dark:border-gray-700 p-3">
        <p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Einladung fuer diesen Gottesdienst</p>
        <div class="grid grid-cols-1 gap-2">
          <select v-model="invitation.targetType" class="form-input">
            <option value="">Kein Einladungsziel</option>
            <option value="DISTRICT_CONGREGATION">Gemeinde im Bezirk</option>
            <option value="EXTERNAL_NOTE">Freitext-Hinweis</option>
          </select>

          <select
            v-if="invitation.targetType === 'DISTRICT_CONGREGATION'"
            v-model="invitation.targetCongregationId"
            class="form-input"
          >
            <option value="">Zielgemeinde auswaehlen…</option>
            <option v-for="cong in invitationTargetOptions" :key="cong.id" :value="cong.id">
              {{ cong.name }}
            </option>
          </select>

          <input
            v-if="invitation.targetType === 'EXTERNAL_NOTE'"
            v-model="invitation.externalNote"
            type="text"
            class="form-input"
            placeholder="z. B. Einladung in Nachbarbezirk"
          />

          <button
            class="btn-secondary justify-center"
            :disabled="invitation.saving || !canSubmitInvitation"
            @click="submitInvitation"
          >
            {{ invitation.saving ? 'Speichern…' : 'Einladung anlegen/aktualisieren' }}
          </button>

          <p v-if="invitation.error" class="text-xs text-red-600 dark:text-red-400">{{ invitation.error }}</p>
          <p v-if="invitation.success" class="text-xs text-green-700 dark:text-green-400">{{ invitation.success }}</p>

          <div class="mt-2 border-t border-gray-200 dark:border-gray-700 pt-2">
            <p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">Bestehende Einladungen</p>
            <p v-if="invitation.loadingExisting" class="text-xs text-gray-500 dark:text-gray-400">Lade…</p>
            <p v-else-if="invitation.existing.length === 0" class="text-xs text-gray-500 dark:text-gray-400">
              Noch keine Einladung gespeichert.
            </p>
            <div v-else class="space-y-1">
              <div
                v-for="existingInvitation in invitation.existing"
                :key="existingInvitation.id"
                class="flex items-center justify-between gap-2 rounded border border-gray-200 dark:border-gray-700 px-2 py-1"
              >
                <button
                  class="text-left text-xs text-gray-700 dark:text-gray-300 hover:underline"
                  @click="useExistingInvitation(existingInvitation)"
                >
                  {{ invitationDisplayLabel(existingInvitation) }}
                </button>
                <button
                  class="text-xs text-red-600 dark:text-red-400 hover:underline"
                  :disabled="invitation.saving"
                  @click="removeInvitation(existingInvitation.id)"
                >
                  Loeschen
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="mb-4 rounded border border-gray-200 dark:border-gray-700 p-3">
        <p class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Gottesdienst verschieben</p>
        <div class="grid grid-cols-3 gap-2">
          <input v-model="modal.moveDate" type="date" class="form-input col-span-2" />
          <input v-model="modal.moveTime" type="time" class="form-input" />
          <input
            v-model.number="modal.moveDurationMinutes"
            type="number"
            min="15"
            step="15"
            class="form-input col-span-2"
            placeholder="Dauer in Minuten"
          />
          <button
            class="btn-secondary justify-center"
            :disabled="modal.moveSaving"
            @click="moveServiceDateTime"
          >
            {{ modal.moveSaving ? 'Verschiebe…' : 'Termin verschieben' }}
          </button>
        </div>
        <p v-if="modal.moveError" class="text-xs text-red-600 dark:text-red-400 mt-2">{{ modal.moveError }}</p>
      </div>

      <label class="form-label">Amtstragende:r</label>
      <AutocompleteInput
        ref="autocompleteRef"
        v-model="modal.leaderInput"
        :options="autocompleteOptions"
        placeholder="Name eingeben oder auswählen…"
        class="mb-3"
      />

      <p v-if="modal.error" class="text-sm text-red-600 dark:text-red-400 mt-2">{{ modal.error }}</p>

      <div class="flex justify-end gap-3 mt-5">
        <button
          v-if="!modal.isGap && modal.assignmentId"
          class="btn-secondary text-red-700 border-red-300 hover:bg-red-50 dark:text-red-300 dark:border-red-700 dark:hover:bg-red-900/20"
          :disabled="modal.saving"
          @click="removeAssignmentFromModal"
        >
          Entfernen
        </button>
        <button class="btn-secondary" @click="closeModal">
          Abbrechen
        </button>
        <button
          v-if="!modal.isGap"
          class="btn-secondary px-4 py-2"
          :disabled="!hasLeaderSelection || modal.saving"
          @click="confirmAssignment"
        >
          {{ modal.saving ? 'Speichern…' : 'Bestaetigen' }}
        </button>
        <button
          class="btn-primary px-4 py-2"
          :disabled="!canSubmit || modal.saving"
          @click="submitAssignment"
        >
          {{ modal.saving ? 'Speichern…' : (modal.isGap ? 'Zuweisen' : 'Speichern') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'
import { useMatrixStore } from '../stores/matrix'
import { useDistrictsStore } from '../stores/districts'
import { useLeadersStore } from '../stores/leaders'
import {
  createInvitations,
  deleteInvitation,
  listEventInvitations,
  type InvitationResponse,
} from '../api/invitations'
import { updateEvent } from '../api/events'
import type { MatrixCell } from '../api/matrix'
import AutocompleteInput, { type AutocompleteOption, type AutocompleteValue } from './AutocompleteInput.vue'

const autocompleteRef = ref<InstanceType<typeof AutocompleteInput> | null>(null)

const matrixStore = useMatrixStore()
const districtsStore = useDistrictsStore()
const leadersStore = useLeadersStore()

// ── Assignment Modal ──────────────────────────────────────────────────────────

const modal = reactive({
  open: false,
  eventId: '',
  assignmentId: null as string | null,
  eventTitle: '',
  date: '',
  congregationName: '',
  congregationId: '',
  isGap: true,
  leaderInput: { id: null, text: '' } as AutocompleteValue,
  saving: false,
  error: '',
  moveDate: '',
  moveTime: '',
  moveDurationMinutes: 90,
  moveSaving: false,
  moveError: '',
})

const canSubmit = computed(() => {
  if (modal.isGap) {
    return modal.leaderInput.id !== null || modal.leaderInput.text.trim().length > 0
  }
  return true
})

const hasLeaderSelection = computed(() => {
  return modal.leaderInput.id !== null || modal.leaderInput.text.trim().length > 0
})

const invitation = reactive({
  targetType: '' as '' | 'DISTRICT_CONGREGATION' | 'EXTERNAL_NOTE',
  targetCongregationId: '',
  externalNote: '',
  existing: [] as InvitationResponse[],
  loadingExisting: false,
  saving: false,
  error: '',
  success: '',
})

const invitationTargetOptions = computed(() => {
  return districtsStore.congregations.filter((c) => c.id !== modal.congregationId)
})

const canSubmitInvitation = computed(() => {
  if (invitation.targetType === 'DISTRICT_CONGREGATION') return !!invitation.targetCongregationId
  if (invitation.targetType === 'EXTERNAL_NOTE') return invitation.externalNote.trim().length > 0
  return false
})

const autocompleteOptions = computed((): AutocompleteOption[] => {
  return leadersStore.activeLeaders().map((l) => ({
    id: l.id,
    label: `${l.rank ? l.rank + ' ' : ''}${l.name}`,
    sublabel: l.congregation_id ? congregationName(l.congregation_id) : undefined,
    isPriority: l.congregation_id === modal.congregationId,
  }))
})

function openModal(cell: MatrixCell, date: string, congregationName: string, congregationId: string) {
  modal.open = true
  modal.eventId = cell.assignment_event_id ?? cell.event_id!
  modal.assignmentId = cell.assignment_id
  modal.eventTitle = cell.event_title ?? ''
  modal.date = date
  modal.congregationName = congregationName
  modal.congregationId = congregationId
  modal.isGap = cell.is_gap
  // Pre-fill with existing assignment if present
  if (cell.leader_id) {
    modal.leaderInput = { id: cell.leader_id, text: cell.leader_name ?? '' }
  } else if (cell.leader_name) {
    modal.leaderInput = { id: null, text: cell.leader_name }
  } else {
    modal.leaderInput = { id: null, text: '' }
  }
  modal.saving = false
  modal.error = ''
  modal.moveSaving = false
  modal.moveError = ''
  modal.moveDate = date
  if (cell.event_start_at) {
    const start = new Date(cell.event_start_at)
    modal.moveTime = `${String(start.getHours()).padStart(2, '0')}:${String(start.getMinutes()).padStart(2, '0')}`
  } else {
    modal.moveTime = '20:00'
  }
  if (cell.event_start_at && cell.event_end_at) {
    const start = new Date(cell.event_start_at)
    const end = new Date(cell.event_end_at)
    const duration = Math.max(15, Math.round((end.getTime() - start.getTime()) / 60000))
    modal.moveDurationMinutes = duration
  } else {
    modal.moveDurationMinutes = 90
  }
  invitation.targetType = ''
  invitation.targetCongregationId = ''
  invitation.externalNote = ''
  invitation.existing = []
  invitation.loadingExisting = false
  invitation.error = ''
  invitation.success = ''
  // Ensure leaders are loaded for this district
  if (matrixStore.districtId && leadersStore.districtId !== matrixStore.districtId) {
    leadersStore.fetchLeaders(matrixStore.districtId)
  }
  void loadEventInvitations()
  // Focus the autocomplete input once the modal DOM is rendered
  nextTick(() => autocompleteRef.value?.focus())
}

function invitationDisplayLabel(existingInvitation: InvitationResponse): string {
  if (
    existingInvitation.target_type === 'DISTRICT_CONGREGATION'
    && existingInvitation.target_congregation_id
  ) {
    const targetName = congregationName(existingInvitation.target_congregation_id)
    return targetName ? `Gemeinde: ${targetName}` : 'Gemeinde (unbekannt)'
  }
  return existingInvitation.external_target_note
    ? `Extern: ${existingInvitation.external_target_note}`
    : 'Externe Einladung'
}

function useExistingInvitation(existingInvitation: InvitationResponse) {
  if (
    existingInvitation.target_type === 'DISTRICT_CONGREGATION'
    && existingInvitation.target_congregation_id
  ) {
    invitation.targetType = 'DISTRICT_CONGREGATION'
    invitation.targetCongregationId = existingInvitation.target_congregation_id
    invitation.externalNote = ''
    return
  }
  invitation.targetType = 'EXTERNAL_NOTE'
  invitation.targetCongregationId = ''
  invitation.externalNote = existingInvitation.external_target_note ?? ''
}

async function loadEventInvitations() {
  invitation.loadingExisting = true
  invitation.error = ''
  try {
    invitation.existing = await listEventInvitations(modal.eventId)
  } catch (e) {
    invitation.error = e instanceof Error ? e.message : 'Einladungen konnten nicht geladen werden'
  } finally {
    invitation.loadingExisting = false
  }
}

async function submitInvitation() {
  invitation.saving = true
  invitation.error = ''
  invitation.success = ''
  try {
    const payload =
      invitation.targetType === 'DISTRICT_CONGREGATION'
        ? {
            target_type: 'DISTRICT_CONGREGATION' as const,
            target_congregation_id: invitation.targetCongregationId,
          }
        : {
            target_type: 'EXTERNAL_NOTE' as const,
            external_target_note: invitation.externalNote.trim(),
          }
    await createInvitations(modal.eventId, [payload])
    invitation.success = 'Einladung gespeichert.'
    await Promise.all([matrixStore.fetch(), loadEventInvitations()])
  } catch (e) {
    invitation.error = e instanceof Error ? e.message : 'Einladung konnte nicht gespeichert werden'
  } finally {
    invitation.saving = false
  }
}

async function removeInvitation(invitationId: string) {
  invitation.saving = true
  invitation.error = ''
  invitation.success = ''
  try {
    await deleteInvitation(invitationId)
    invitation.success = 'Einladung geloescht.'
    await Promise.all([matrixStore.fetch(), loadEventInvitations()])
  } catch (e) {
    invitation.error = e instanceof Error ? e.message : 'Einladung konnte nicht geloescht werden'
  } finally {
    invitation.saving = false
  }
}

function closeModal() {
  modal.open = false
}

async function submitAssignment() {
  if (!canSubmit.value) return
  modal.saving = true
  modal.error = ''
  try {
    const leaderText = modal.leaderInput.text.trim()
    const hasLeader = modal.leaderInput.id !== null || leaderText.length > 0

    if (!hasLeader) {
      await matrixStore.clearAssignment(modal.eventId, modal.assignmentId)
    } else if (modal.leaderInput.id !== null) {
      await matrixStore.assign(modal.eventId, modal.assignmentId, { leaderId: modal.leaderInput.id })
    } else {
      await matrixStore.assign(modal.eventId, modal.assignmentId, { leaderName: leaderText })
    }
    closeModal()
  } catch (e) {
    modal.error = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally {
    modal.saving = false
  }
}

async function confirmAssignment() {
  if (!hasLeaderSelection.value) {
    modal.error = 'Bitte waehle zuerst eine:n Amtstragende:n aus.'
    return
  }
  modal.saving = true
  modal.error = ''
  try {
    const leaderText = modal.leaderInput.text.trim()
    if (modal.leaderInput.id !== null) {
      await matrixStore.assign(
        modal.eventId,
        modal.assignmentId,
        { leaderId: modal.leaderInput.id },
        'CONFIRMED',
      )
    } else {
      await matrixStore.assign(
        modal.eventId,
        modal.assignmentId,
        { leaderName: leaderText },
        'CONFIRMED',
      )
    }
    closeModal()
  } catch (e) {
    modal.error = e instanceof Error ? e.message : 'Fehler beim Bestaetigen'
  } finally {
    modal.saving = false
  }
}

async function removeAssignmentFromModal() {
  modal.saving = true
  modal.error = ''
  try {
    await matrixStore.clearAssignment(modal.eventId, modal.assignmentId)
    closeModal()
  } catch (e) {
    modal.error = e instanceof Error ? e.message : 'Fehler beim Entfernen'
  } finally {
    modal.saving = false
  }
}

function combineLocalDateTime(dateText: string, timeText: string): Date {
  const [year, month, day] = dateText.split('-').map(Number)
  const [hour, minute] = timeText.split(':').map(Number)
  return new Date(year, month - 1, day, hour, minute, 0, 0)
}

async function moveServiceDateTime() {
  if (!modal.eventId || !modal.moveDate || !modal.moveTime) {
    modal.moveError = 'Datum und Uhrzeit sind erforderlich.'
    return
  }
  if (!Number.isFinite(modal.moveDurationMinutes) || modal.moveDurationMinutes < 15) {
    modal.moveError = 'Dauer muss mindestens 15 Minuten betragen.'
    return
  }

  modal.moveSaving = true
  modal.moveError = ''
  try {
    const localStart = combineLocalDateTime(modal.moveDate, modal.moveTime)
    const localEnd = new Date(localStart.getTime() + modal.moveDurationMinutes * 60000)
    await updateEvent(modal.eventId, {
      start_at: localStart.toISOString(),
      end_at: localEnd.toISOString(),
    })
    await matrixStore.fetch()
    closeModal()
  } catch (e) {
    modal.moveError = e instanceof Error ? e.message : 'Verschieben fehlgeschlagen'
  } finally {
    modal.moveSaving = false
  }
}

function congregationName(congregationId: string): string {
  return districtsStore.congregations.find((c) => c.id === congregationId)?.name ?? ''
}

function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-')
  return `${day}.${month}.${year}`
}

defineExpose({ open: openModal })
</script>
