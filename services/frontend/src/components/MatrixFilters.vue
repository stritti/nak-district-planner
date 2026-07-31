<template>
  <!-- Filter-Leiste -->
  <div class="filter-bar mb-4">

    <!-- Schnellfilter -->
    <div class="flex items-center gap-2 mb-3 flex-wrap">
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
      <div class="w-full sm:w-auto">
        <label class="filter-label">Bezirk</label>
        <select
          v-model="districtsStore.selectedDistrictId"
          class="form-select"
        >
          <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">
            {{ d.name }}
          </option>
        </select>
      </div>

      <div v-if="districtsStore.groups.length > 0" class="w-full sm:w-auto">
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

      <div class="w-full sm:w-auto">
        <label class="filter-label">Sortierung</label>
        <select
          :value="matrixSortMode"
          class="form-select"
          @change="onSortModeChange"
        >
          <option value="default">Standard</option>
          <option value="grouped">Nach Gruppen</option>
        </select>
      </div>

      <div class="w-full sm:w-auto">
        <label class="filter-label">Von</label>
        <input
          v-model="matrixStore.fromDt"
          type="date"
          class="form-select"
        />
      </div>

      <div class="w-full sm:w-auto">
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

      <button
        class="flex items-center gap-1.5 bg-teal-600 text-white text-sm px-4 py-1.5 rounded hover:bg-teal-700 disabled:opacity-50"
        :disabled="!matrixStore.districtId || matrixStore.loading"
        @click="emit('release')"
      >
        <ArrowPathIcon class="h-4 w-4" />
        Freigabe
      </button>

      <div class="sm:ml-auto inline-flex items-center rounded-md border border-gray-300 dark:border-gray-600 overflow-hidden">
        <button
          class="px-3 py-1.5 text-xs font-medium transition-colors"
          :class="!compactMode
            ? 'bg-blue-600 text-white'
            : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
          @click="emit('update:compactMode', false)"
        >
          Normal
        </button>
        <button
          class="px-3 py-1.5 text-xs font-medium transition-colors"
          :class="compactMode
            ? 'bg-blue-600 text-white'
            : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'"
          @click="emit('update:compactMode', true)"
        >
          Kompakt
        </button>
      </div>
    </div>

    <p v-if="releaseMessage" class="mt-2 text-xs text-teal-700 dark:text-teal-400">
      {{ releaseMessage }}
    </p>
    <p v-if="generationMessage" class="mt-2 text-xs text-green-700 dark:text-green-400">
      {{ generationMessage }}
    </p>
    <p v-if="generationError" class="mt-2 text-xs text-red-600 dark:text-red-400">
      {{ generationError }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowDownTrayIcon, ArrowPathIcon } from '@heroicons/vue/24/outline'
import { useMatrixStore } from '../stores/matrix'
import { useDistrictsStore } from '../stores/districts'
import { exportMatrixToExcel } from '../composables/useExcelExport'

const props = defineProps<{
  compactMode: boolean
  matrixSortMode: 'default' | 'grouped'
  releaseMessage: string
}>()

const emit = defineEmits<{
  (e: 'update:compactMode', value: boolean): void
  (e: 'update:matrixSortMode', value: 'default' | 'grouped'): void
  (e: 'release'): void
}>()

const matrixStore = useMatrixStore()
const districtsStore = useDistrictsStore()

function onSortModeChange(event: Event) {
  emit('update:matrixSortMode', (event.target as HTMLSelectElement).value as 'default' | 'grouped')
}

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

// ── Excel Export / Draft-Generierung ─────────────────────────────────────────

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
</script>
