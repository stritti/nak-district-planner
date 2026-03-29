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
      </div>
    </div>

    <!-- Loading / Error -->
    <div v-if="matrixStore.loading" class="text-sm text-gray-500 dark:text-gray-400">Lade…</div>
    <div v-else-if="matrixStore.error" class="text-sm text-red-600 dark:text-red-400">{{ matrixStore.error }}</div>

    <!-- Matrix Table -->
    <div
      v-else-if="matrixStore.matrix && matrixStore.matrix.dates.length > 0"
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
                  @click="openModal(row.cells[date], date, row.congregation_name, row.congregation_id)"
                >
                  <div class="flex items-center gap-1 font-bold text-red-700 dark:text-red-400">
                    <ExclamationTriangleIcon class="h-3.5 w-3.5 shrink-0" />
                    LÜCKE
                  </div>
                  <div class="text-red-600 dark:text-red-400 truncate max-w-[100px]">{{ row.cells[date].event_title }}</div>
                </button>
                <button
                  v-else
                  class="w-full text-left hover:opacity-75"
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
      v-else-if="matrixStore.matrix && matrixStore.matrix.dates.length === 0"
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
            {{ modal.isGap ? 'Amtstragenden zuweisen' : 'Zuweisung bearbeiten' }}
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

        <label class="form-label">Amtstragender</label>
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
import { ArrowPathIcon, ExclamationTriangleIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { useMatrixStore } from '@/stores/matrix'
import { useDistrictsStore } from '@/stores/districts'
import { useLeadersStore } from '@/stores/leaders'
import type { MatrixCell } from '@/api/matrix'
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
    await Promise.all([
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
    await Promise.all([
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
})

const canSubmit = computed(() => {
  return modal.leaderInput.id !== null || modal.leaderInput.text.trim().length > 0
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
  modal.eventId = cell.event_id!
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
  // Ensure leaders are loaded for this district
  if (matrixStore.districtId && leadersStore.districtId !== matrixStore.districtId) {
    leadersStore.fetchLeaders(matrixStore.districtId)
  }
  // Focus the autocomplete input once the modal DOM is rendered
  nextTick(() => autocompleteRef.value?.focus())
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
</script>
