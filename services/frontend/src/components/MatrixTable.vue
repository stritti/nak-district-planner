<template>
  <!-- Matrix Table -->
  <div
    v-if="!matrixStore.loading && !matrixStore.error && matrixStore.matrix && matrixStore.matrix.dates.length > 0"
    class="overflow-x-auto"
  >
    <table :class="tableClass">
      <thead>
        <tr>
          <th
            class="sticky left-0 z-10 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 text-left font-medium text-gray-700 dark:text-gray-300"
            :class="compactMode ? 'px-2 py-2 w-[120px] min-w-[120px]' : 'px-3 py-2 w-[170px] min-w-[170px]'"
          >
            Gemeinde
          </th>
          <th
            v-for="date in matrixStore.matrix.dates"
            :key="date"
            class="border text-center font-medium"
            :class="[
              compactMode ? 'px-1.5 py-2 min-w-[92px]' : 'px-2.5 py-2 min-w-[118px]',
              matrixStore.matrix.holidays[date]?.length
                ? 'border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 text-amber-900 dark:text-amber-200'
                : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300',
            ]"
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
        <tr v-for="row in displayedRows" :key="row.congregation_id">
          <td
            class="sticky left-0 z-10 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 font-medium text-gray-800 dark:text-gray-200"
            :class="compactMode ? 'px-2 py-2' : 'px-3 py-2'"
          >
            {{ row.congregation_name }}
            <div v-if="row.group_name" class="text-[10px] font-normal text-gray-500 dark:text-gray-400">
              {{ row.group_name }}
            </div>
          </td>
          <td
            v-for="date in matrixStore.matrix.dates"
            :key="date"
            class="border border-gray-300 dark:border-gray-600 align-top"
            :class="[compactMode ? 'px-1.5 py-1.5' : 'px-2.5 py-2', cellClass(row.cells[date])]"
          >
            <template v-if="row.cells[date]?.event_id">
              <button
                v-if="row.cells[date].is_gap"
                class="w-full text-left"
                :disabled="row.cells[date].is_assignment_editable === false"
                @click="openCellModal(row.cells[date], date, row.congregation_name, row.congregation_id)"
              >
                <div class="flex items-center gap-1 font-bold text-red-700 dark:text-red-400">
                  <ExclamationTriangleIcon class="h-3.5 w-3.5 shrink-0" />
                  LÜCKE
                </div>
                 <div
                   v-overflow-title="row.cells[date].event_title ?? ''"
                   :class="gapTitleClass"
                 >
                   {{ row.cells[date].event_title }}
                 </div>
                <!-- Deviation indicator for gap cells -->
                <div
                  v-if="row.cells[date].has_deviation"
                  class="flex items-center gap-1 mt-1"
                >
                  <span class="inline-block w-2 h-2 rounded-full bg-amber-500 shrink-0"></span>
                  <span class="text-[10px] text-amber-700 dark:text-amber-400">
                    Plan: {{ formatTime(row.cells[date].planned_time) }}
                    · Ist: {{ formatTime(row.cells[date].actual_start_at) }}
                  </span>
                </div>
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
                @click="openCellModal(row.cells[date], date, row.congregation_name, row.congregation_id)"
              >
                <!-- Deviation Indicator -->
                <div v-if="row.cells[date]?.has_deviation === true" class="flex items-center gap-1">
                  <DeviationIndicator
                    :has-deviation="true"
                    :planned-time="formatTime(row.cells[date]?.planned_time)"
                    :actual-time="formatTime(row.cells[date]?.actual_start_at)"
                    :start-diff-minutes="row.cells[date]?.deviation_start_diff_minutes ?? null"
                    :end-diff-minutes="row.cells[date]?.deviation_end_diff_minutes ?? null"
                    :compact="compactMode"
                  />
                </div>

                <div
                  v-overflow-title="row.cells[date].event_title ?? ''"
                  :class="eventTitleClass"
                >
                  {{ row.cells[date].event_title }}
                </div>
                <div
                  v-if="row.cells[date].leader_name"
                  v-overflow-title="row.cells[date].leader_name ?? ''"
                  :class="leaderNameClass"
                >
                  {{ row.cells[date].leader_name }}
                </div>
                <EventApprovalStatusBadge
                  v-if="row.cells[date].approval_status"
                  :status="row.cells[date].approval_status"
                  class="mt-0.5"
                />
                <div v-if="row.cells[date].category" class="text-gray-400 dark:text-gray-500">
                  {{ row.cells[date].category }}
                </div>
                <!-- Deviation indicator for non-gap cells -->
                <div
                  v-if="row.cells[date].has_deviation"
                  class="flex items-center gap-1 mt-0.5"
                >
                  <span class="inline-block w-2 h-2 rounded-full bg-amber-500 shrink-0"></span>
                  <span class="text-[10px] text-amber-700 dark:text-amber-400" :title="'Geplante Zeit: ' + formatTime(row.cells[date].planned_time) + ' · Tatsächliche Zeit: ' + formatTime(row.cells[date].actual_start_at)">
                    Abweichung
                  </span>
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
</template>

<script setup lang="ts">
import type { Directive } from 'vue'
import { computed } from 'vue'
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { useMatrixStore } from '../stores/matrix'
import { useDistrictsStore } from '../stores/districts'
import type { MatrixCell, MatrixRow } from '../api/matrix'
import { sortMatrixRows } from '../utils/matrixRows'
import DeviationIndicator from './DeviationIndicator.vue'
import EventApprovalStatusBadge from './EventApprovalStatusBadge.vue'

const props = defineProps<{
  compactMode: boolean
  matrixSortMode: 'default' | 'grouped'
}>()

const emit = defineEmits<{
  (e: 'open-modal', payload: {
    cell: MatrixCell
    date: string
    congregationName: string
    congregationId: string
  }): void
}>()

const matrixStore = useMatrixStore()
const districtsStore = useDistrictsStore()

type OverflowTitleEl = HTMLElement & {
  __overflowTitleHandler__?: () => void
}

function applyOverflowTitle(el: OverflowTitleEl, value: string) {
  const text = value.trim()
  if (!text) {
    el.removeAttribute('title')
    return
  }
  if (el.scrollWidth > el.clientWidth) {
    el.setAttribute('title', text)
    return
  }
  el.removeAttribute('title')
}

const vOverflowTitle: Directive<OverflowTitleEl, string> = {
  mounted(el, binding) {
    const handler = () => applyOverflowTitle(el, binding.value ?? '')
    el.__overflowTitleHandler__ = handler
    requestAnimationFrame(handler)
    el.addEventListener('mouseenter', handler)
  },
  updated(el, binding) {
    requestAnimationFrame(() => applyOverflowTitle(el, binding.value ?? ''))
  },
  unmounted(el) {
    if (el.__overflowTitleHandler__) {
      el.removeEventListener('mouseenter', el.__overflowTitleHandler__)
      delete el.__overflowTitleHandler__
    }
  },
}

const tableClass = computed(() => {
  return [
    'w-full table-fixed border-collapse',
    props.compactMode ? 'text-[11px] matrix-table--compact' : 'text-xs matrix-table--normal',
  ]
})

const gapTitleClass = computed(() => {
  return [
    'matrix-ellipsis matrix-cell-gap text-red-600 dark:text-red-400',
    props.compactMode ? 'text-[10px]' : 'text-[11px]',
  ]
})

const eventTitleClass = computed(() => {
  return [
    'matrix-ellipsis matrix-cell-title font-medium text-gray-800 dark:text-gray-200',
    props.compactMode ? 'text-[10px]' : 'text-[11px]',
  ]
})

const leaderNameClass = computed(() => {
  return [
    'matrix-ellipsis matrix-cell-subtitle text-gray-500 dark:text-gray-400',
    props.compactMode ? 'text-[10px]' : 'text-[11px]',
  ]
})

const displayedRows = computed((): MatrixRow[] => {
  const rows = matrixStore.matrix?.rows ?? []
  return sortMatrixRows(rows, props.matrixSortMode)
})

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
  if (cell.has_deviation) return 'bg-amber-50 dark:bg-amber-900/10 cursor-pointer hover:bg-amber-100 dark:hover:bg-amber-900/20 ring-1 ring-inset ring-amber-300 dark:ring-amber-700'
  return 'bg-white dark:bg-gray-900 cursor-pointer'
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return ''
  // Handle full ISO datetime or time string
  if (iso.includes('T')) {
    const d = new Date(iso)
    return d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  }
  return iso.slice(0, 5)
}

function openCellModal(cell: MatrixCell, date: string, congregationName: string, congregationId: string) {
  emit('open-modal', { cell, date, congregationName, congregationId })
}
</script>

<style scoped>
.matrix-ellipsis {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.matrix-table--normal .matrix-cell-gap {
  max-width: 14ch;
}

.matrix-table--normal .matrix-cell-title {
  max-width: 16ch;
}

.matrix-table--normal .matrix-cell-subtitle {
  max-width: 18ch;
}

.matrix-table--compact .matrix-cell-gap {
  max-width: 11ch;
}

.matrix-table--compact .matrix-cell-title {
  max-width: 12ch;
}

.matrix-table--compact .matrix-cell-subtitle {
  max-width: 13ch;
}

@media (min-width: 1280px) {
  .matrix-table--normal .matrix-cell-gap {
    max-width: 18ch;
  }

  .matrix-table--normal .matrix-cell-title {
    max-width: 22ch;
  }

  .matrix-table--normal .matrix-cell-subtitle {
    max-width: 24ch;
  }

  .matrix-table--compact .matrix-cell-gap {
    max-width: 13ch;
  }

  .matrix-table--compact .matrix-cell-title {
    max-width: 14ch;
  }

  .matrix-table--compact .matrix-cell-subtitle {
    max-width: 15ch;
  }
}
</style>
