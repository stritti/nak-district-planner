<template>
  <div class="p-2 sm:p-4">
    <h1 class="page-title">Dienstplan-Matrix</h1>

    <!-- Filter-Leiste -->
    <MatrixFilters
      :compact-mode="compactMode"
      :matrix-sort-mode="matrixSortMode"
      :release-message="releaseMessage"
      @update:compact-mode="setCompactMode"
      @update:matrix-sort-mode="onSortModeChange"
      @release="showReleaseDialog = true"
    />

    <!-- Loading / Error -->
    <div v-if="matrixStore.loading" class="text-sm text-gray-500 dark:text-gray-400">Lade…</div>
    <div v-else-if="matrixStore.error" class="text-sm text-red-600 dark:text-red-400">{{ matrixStore.error }}</div>

    <!-- Matrix Table -->
    <MatrixTable
      :compact-mode="compactMode"
      :matrix-sort-mode="matrixSortMode"
      @open-modal="openModal"
    />

    <AssignmentModal ref="assignmentModalRef" />

    <MonthlyReleaseDialog
      :open="showReleaseDialog"
      :district-id="matrixStore.districtId"
      @close="showReleaseDialog = false"
      @released="onReleaseComplete"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useMatrixStore } from '../stores/matrix'
import { useDistrictsStore } from '../stores/districts'
import { useLeadersStore } from '../stores/leaders'
import type { MatrixCell } from '../api/matrix'
import MatrixFilters from '../components/MatrixFilters.vue'
import MatrixTable from '../components/MatrixTable.vue'
import AssignmentModal from '../components/AssignmentModal.vue'
import MonthlyReleaseDialog from '../components/MonthlyReleaseDialog.vue'

const matrixStore = useMatrixStore()
const districtsStore = useDistrictsStore()
const leadersStore = useLeadersStore()

const COMPACT_MODE_STORAGE_KEY = 'matrix.compactMode'
const MATRIX_SORT_MODE_STORAGE_KEY = 'matrix.sortMode'
const compactMode = ref(false)
const matrixSortMode = ref<'default' | 'grouped'>('default')
const showReleaseDialog = ref(false)
const releaseMessage = ref('')

function onReleaseComplete(count: number) {
  showReleaseDialog.value = false
  releaseMessage.value = `${count} Termin${count === 1 ? '' : 'e'} bestätigt.`
  setTimeout(() => { releaseMessage.value = '' }, 4000)
  matrixStore.fetch() // refresh matrix after release
}

function setCompactMode(enabled: boolean) {
  compactMode.value = enabled
  localStorage.setItem(COMPACT_MODE_STORAGE_KEY, enabled ? '1' : '0')
}

function saveSortMode() {
  localStorage.setItem(MATRIX_SORT_MODE_STORAGE_KEY, matrixSortMode.value)
}

function onSortModeChange(value: 'default' | 'grouped') {
  matrixSortMode.value = value
  saveSortMode()
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  compactMode.value = localStorage.getItem(COMPACT_MODE_STORAGE_KEY) === '1'
  matrixSortMode.value = localStorage.getItem(MATRIX_SORT_MODE_STORAGE_KEY) === 'grouped'
    ? 'grouped'
    : 'default'
  if (districtsStore.districts.length === 0) await districtsStore.fetchDistricts()
  syncDistrictSelectionFromStore()
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
  matrixStore.districtId = districtsStore.selectedDistrictId
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

watch(
  () => districtsStore.selectedDistrictId,
  async (districtId) => {
    if (districtId === matrixStore.districtId) return
    await onDistrictChange()
  },
)

function syncDistrictSelectionFromStore() {
  districtsStore.ensureSelectedDistrict()
  matrixStore.districtId = districtsStore.selectedDistrictId
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function monthRange(offset: number): { from: string; to: string } {
  const now = new Date()
  return {
    from: localDate(new Date(now.getFullYear(), now.getMonth() + offset, 1)),
    to:   localDate(new Date(now.getFullYear(), now.getMonth() + offset + 1, 0)),
  }
}

function localDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// ── Assignment Modal bridge ───────────────────────────────────────────────────

const assignmentModalRef = ref<InstanceType<typeof AssignmentModal> | null>(null)

function openModal(payload: {
  cell: MatrixCell
  date: string
  congregationName: string
  congregationId: string
}) {
  assignmentModalRef.value?.open(payload.cell, payload.date, payload.congregationName, payload.congregationId)
}
</script>
