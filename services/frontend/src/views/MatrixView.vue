<template>
  <div class="p-6">
    <h1 class="page-title mb-4">Dienstplan-Matrix</h1>

    <!-- Filter-Leiste -->
    <div class="filter-bar mb-6">

      <!-- Schnellfilter -->
      <div class="flex items-center gap-2 mb-3">
        <span class="text-xs text-gray-400 dark:text-gray-500 font-medium mr-1">Schnellfilter:</span>
        <button
          v-for="preset in presets"
          :key="preset.key"
          class="text-xs px-3 py-1 rounded-full border transition-colors"
          :class="activePreset === preset.key
            ? 'bg-blue-600 text-white border-blue-600'
            : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-blue-400 hover:text-blue-600 dark:hover:border-blue-500 dark:hover:text-blue-400'"
          @click="setPreset(preset.key)"
        >
          {{ preset.label }}
        </button>
      </div>

      <!-- Bezirk + Datumsfelder -->
      <div class="flex flex-wrap items-end gap-3">
        <div>
          <label class="filter-label">Bezirk</label>
          <select
            v-model="matrixStore.districtId"
            class="form-select"
            @change="onDistrictChange"
          >
            <option value="">Bezirk wählen…</option>
            <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">
              {{ d.name }}
            </option>
          </select>
        </div>

        <div v-if="districtsStore.groups.length > 0">
          <label class="filter-label">Gruppe</label>
          <select
            v-model="matrixStore.groupId"
            class="form-select"
            @change="matrixStore.fetch()"
          >
            <option value="">Alle Gruppen</option>
            <option v-for="g in districtsStore.groups" :key="g.id" :value="g.id">
              {{ g.name }}
            </option>
          </select>
        </div>

        <div>
          <label class="filter-label">Von</label>
          <input
            v-model="matrixStore.fromDt"
            type="date"
            class="form-select"
          />
        </div>

        <div>
          <label class="filter-label">Bis</label>
          <input
            v-model="matrixStore.toDt"
            type="date"
            class="form-select"
          />
        </div>

        <button
          class="btn-primary px-4 py-1.5"
          :disabled="!matrixStore.districtId || !matrixStore.fromDt || !matrixStore.toDt || matrixStore.loading"
          @click="matrixStore.fetch()"
        >
          <ArrowPathIcon class="h-4 w-4" :class="matrixStore.loading ? 'animate-spin' : ''" />
          Anzeigen
        </button>

        <button
          class="flex items-center gap-1.5 bg-green-600 text-white text-sm px-4 py-1.5 rounded hover:bg-green-700 disabled:opacity-50"
          :disabled="!matrixStore.matrix || matrixStore.matrix.dates.length === 0 || matrixStore.loading || exporting"
          @click="triggerMatrixExport"
        >
          <ArrowDownTrayIcon class="h-4 w-4" />
          {{ exporting ? 'Exportiere…' : 'Excel' }}
        </button>

        <button
          class="flex items-center gap-1.5 bg-indigo-600 text-white text-sm px-4 py-1.5 rounded hover:bg-indigo-700 disabled:opacity-50"
          :disabled="!matrixStore.districtId || !matrixStore.fromDt || !matrixStore.toDt || matrixStore.loading || generatingDrafts"
          @click="triggerRangeDraftGeneration"
        >
          <ArrowPathIcon class="h-4 w-4" :class="generatingDrafts ? 'animate-spin' : ''" />
          {{ generatingDrafts ? 'Generiere…' : 'Entwuerfe erzeugen' }}
        </button>
      </div>

      <p v-if="generationMessage" class="mt-2 text-xs text-green-700 dark:text-green-400">
        {{ generationMessage }}
      </p>
      <p v-if="generationError" class="mt-2 text-xs text-red-600 dark:text-red-400">
        {{ generationError }}
      </p>
    </div>

    <!-- Loading / Error -->
    <div v-if="matrixStore.loading" class="text-sm text-gray-500 dark:text-gray-400">Lade…</div>
    <div v-else-if="matrixStore.error" class="text-sm text-red-600 dark:text-red-400">{{ matrixStore.error }}</div>

    <!-- Matrix Table -->
    <div
      v-if="!matrixStore.loading && !matrixStore.error && matrixStore.matrix && matrixStore.matrix.dates.length > 0"
      class="overflow-x-auto"
    >
      <table class="border-collapse text-xs">
        <thead>
          <tr>
            <th class="sticky left-0 z-10 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300 min-w-[140px]">
              Gemeinde
            </th>
            <th
              v-for="date in matrixStore.matrix.dates"
              :key="date"
              class="border px-2 py-2 text-center font-medium min-w-[110px]"
              :class="matrixStore.matrix.holidays[date]?.length
                ? 'border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 text-amber-900 dark:text-amber-200'
                : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'"
            >
              <div class="text-[11px] font-normal" :class="matrixStore.matrix.holidays[date]?.length ? 'text-amber-500 dark:text-amber-400' : 'text-gray-400 dark:text-gray-500'">
                {{ formatWeekday(date) }}
              </div>
              <div>{{ formatDate(date) }}</div>
              <div
                v-if="matrixStore.matrix.holidays[date]?.length"
                class="mt-1 space-y-0.5"
              >
                <span
                  v-for="name in matrixStore.matrix.holidays[date]"
                  :key="name"
                  class="block text-[10px] leading-tight font-medium text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/30 rounded px-1 py-0.5"
                >
                  {{ name }}
                </span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in matrixStore.matrix.rows" :key="row.congregation_id">
            <td class="sticky left-0 z-10 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 px-3 py-2 font-medium text-gray-800 dark:text-gray-200">
              {{ row.congregation_name }}
            </td>
            <td
              v-for="date in matrixStore.matrix.dates"
              :key="date"
              class="border border-gray-300 dark:border-gray-600 px-2 py-1.5 align-top"
              :class="cellClass(row.cells[date])"
            >
              <template v-if="row.cells[date]?.event_id">
                <button
                  v-if="row.cells[date].is_gap"
                  class="w-full text-left"
                  :disabled="row.cells[date].is_assignment_editable === false"
                  @click="openModal(row.cells[date], date, row.congregation_name, row.congregation_id)"
                >
                  <div class="flex items-center gap-1 font-bold text-red-700 dark:text-red-400">
                    <ExclamationTriangleIcon class="h-3.5 w-3.5 shrink-0" />
                    LÜCKE
                  </div>
                  <div class="text-red-600 dark:text-red-400 truncate max-w-[100px]">{{ row.cells[date].event_title }}</div>
                  <div
                    v-if="(row.cells[date].invitation_count ?? 0) > 0"
                    class="text-[10px] text-sky-700 dark:text-sky-300"
                  >
                    Einladungen: {{ row.cells[date].invitation_count }}
                  </div>
                </button>
                <button
                  v-else
                  class="w-full text-left hover:opacity-75"
                  :disabled="row.cells[date].is_assignment_editable === false"
                  @click="openModal(row.cells[date], date, row.congregation_name, row.congregation_id)"
                >
                  <div class="font-medium text-gray-800 dark:text-gray-200 truncate max-w-[100px]">
                    {{ row.cells[date].event_title }}
                  </div>
                  <div v-if="row.cells[date].leader_name" class="text-gray-500 dark:text-gray-400 truncate max-w-[100px]">
                    {{ row.cells[date].leader_name }}
                  </div>
                  <div v-if="row.cells[date].category" class="text-gray-400 dark:text-gray-500">
                    {{ row.cells[date].category }}
                  </div>
                  <div
                    v-if="row.cells[date].invitation_source_congregation_name"
                    class="text-[10px] text-amber-700 dark:text-amber-300"
                  >
                    Einladung von {{ row.cells[date].invitation_source_congregation_name }}
                  </div>
                  <div
                    v-if="(row.cells[date].invitation_count ?? 0) > 0"
                    class="text-[10px] text-sky-700 dark:text-sky-300"
                  >
                    Einladungen: {{ row.cells[date].invitation_count }}
                  </div>
                  <div
                    v-if="row.cells[date].is_assignment_editable === false"
                    class="text-[10px] text-amber-600 dark:text-amber-400"
                  >
                    Dienstleiterpflege in Host-Gemeinde
                  </div>
                </button>
              </template>
              <template v-else>
                <span class="text-gray-300 dark:text-gray-600">–</span>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="!matrixStore.loading && !matrixStore.error && matrixStore.matrix && matrixStore.matrix.dates.length === 0"
      class="text-sm text-gray-500 dark:text-gray-400"
    >
      Keine Ereignisse im gewählten Zeitraum.
    </div>

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
          <button class="btn-secondary" @click="closeModal">
            Abbrechen
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

  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ArrowDownTrayIcon, ArrowPathIcon, ExclamationTriangleIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { useMatrixStore } from '@/stores/matrix'
import { useDistrictsStore } from '@/stores/districts'
import { useLeadersStore } from '@/stores/leaders'
import {
  createInvitations,
  deleteInvitation,
  listEventInvitations,
  type InvitationResponse,
} from '@/api/invitations'
import { updateEvent } from '@/api/events'
import type { MatrixCell } from '@/api/matrix'
import { exportMatrixToExcel } from '@/composables/useExcelExport'
import AutocompleteInput, { type AutocompleteOption, type AutocompleteValue } from '@/components/AutocompleteInput.vue'

const autocompleteRef = ref<InstanceType<typeof AutocompleteInput> | null>(null)

const matrixStore = useMatrixStore()
const districtsStore = useDistrictsStore()
const leadersStore = useLeadersStore()

// ── Preset-Filter ────────────────────────────────────────────────────────────

function localDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function monthRange(offset: number): { from: string; to: string } {
  const now = new Date()
  return {
    from: localDate(new Date(now.getFullYear(), now.getMonth() + offset, 1)),
    to:   localDate(new Date(now.getFullYear(), now.getMonth() + offset + 1, 0)),
  }
}

const presets = [
  { key: 'current', label: 'Aktueller Monat' },
  { key: 'next',    label: 'Kommender Monat' },
]

const activePreset = computed(() => {
  const curr = monthRange(0)
  const next = monthRange(1)
  if (matrixStore.fromDt === curr.from && matrixStore.toDt === curr.to) return 'current'
  if (matrixStore.fromDt === next.from && matrixStore.toDt === next.to) return 'next'
  return null
})

function setPreset(key: string) {
  const offset = key === 'next' ? 1 : 0
  const { from, to } = monthRange(offset)
  matrixStore.fromDt = from
  matrixStore.toDt = to
  if (matrixStore.districtId) matrixStore.fetch()
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  if (districtsStore.districts.length === 0) await districtsStore.fetchDistricts()
  // Pre-select current month if no range set yet
  if (!matrixStore.fromDt || !matrixStore.toDt) {
    const { from, to } = monthRange(0)
    matrixStore.fromDt = from
    matrixStore.toDt = to
  }
  // Auto-fetch if district already selected (e.g. navigating back)
  if (matrixStore.districtId) {
    await Promise.allSettled([
      districtsStore.fetchGroups(matrixStore.districtId),
      districtsStore.fetchCongregations(matrixStore.districtId),
      leadersStore.fetchLeaders(matrixStore.districtId),
    ])
    matrixStore.fetch()
  }
})

async function onDistrictChange() {
  matrixStore.matrix = null
  matrixStore.groupId = ''
  if (matrixStore.districtId) {
    await Promise.allSettled([
      districtsStore.fetchGroups(matrixStore.districtId),
      districtsStore.fetchCongregations(matrixStore.districtId),
      leadersStore.fetchLeaders(matrixStore.districtId),
    ])
    if (matrixStore.fromDt && matrixStore.toDt) {
      matrixStore.fetch()
    }
  }
}

function congregationName(congregationId: string): string {
  return districtsStore.congregations.find((c) => c.id === congregationId)?.name ?? ''
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const WEEKDAY_SHORT = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']

function formatDate(iso: string): string {
  const [year, month, day] = iso.split('-')
  return `${day}.${month}.${year}`
}

function formatWeekday(iso: string): string {
  // Parse as local date to avoid UTC-offset shifts
  const [year, month, day] = iso.split('-').map(Number)
  return WEEKDAY_SHORT[new Date(year, month - 1, day).getDay()]
}

function cellClass(cell: MatrixCell | undefined): string {
  if (!cell?.event_id) return 'bg-white dark:bg-gray-900'
  if (cell.is_gap) return 'bg-red-100 dark:bg-red-900/20 cursor-pointer hover:bg-red-200 dark:hover:bg-red-900/30 ring-1 ring-inset ring-red-300 dark:ring-red-700'
  if (cell.is_assignment_editable === false) return 'bg-white dark:bg-gray-900 opacity-80'
  return 'bg-white dark:bg-gray-900 cursor-pointer'
}

// ── Assignment Modal ──────────────────────────────────────────────────────────

const modal = reactive({
  open: false,
  eventId: '',
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
    if (modal.leaderInput.id !== null) {
      await matrixStore.assign(modal.eventId, { leaderId: modal.leaderInput.id })
    } else {
      await matrixStore.assign(modal.eventId, { leaderName: modal.leaderInput.text.trim() })
    }
    closeModal()
  } catch (e) {
    modal.error = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally {
    modal.saving = false
  }
}

// ── Excel Export ──────────────────────────────────────────────────────────────

const exporting = ref(false)
const generatingDrafts = ref(false)
const generationMessage = ref('')
const generationError = ref('')

async function triggerMatrixExport() {
  if (!matrixStore.matrix) return
  exporting.value = true
  try {
    await exportMatrixToExcel(matrixStore.matrix, matrixStore.fromDt, matrixStore.toDt)
  } finally {
    exporting.value = false
  }
}

async function triggerRangeDraftGeneration() {
  generationMessage.value = ''
  generationError.value = ''
  generatingDrafts.value = true
  try {
    const result = await matrixStore.generateDraftsForCurrentRange()
    generationMessage.value = `Entwuerfe erzeugt: ${result.created}, bereits vorhanden: ${result.skipped_existing}, im Bereich vorhanden: ${result.generated_in_requested_range}`
  } catch (e) {
    generationError.value = e instanceof Error ? e.message : 'Entwurfsgenerierung fehlgeschlagen'
  } finally {
    generatingDrafts.value = false
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
</script>
