<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div class="p-2 sm:p-4">
    <h1 class="page-title">Dienstplan-Matrix</h1>
    <ContextualHelp context="matrix" />

    <!-- Filter-Leiste -->
    <MatrixFilters
      :compact-mode="compactMode"
      :matrix-sort-mode="matrixSortMode"
      @update:compact-mode="setCompactMode"
      @update:matrix-sort-mode="onSortModeChange"
      @release="showReleaseDialog = true"
    />

    <!-- Loading / Error -->
    <MatrixSkeleton v-if="matrixStore.loading" />
    <div v-else-if="matrixStore.error" class="text-sm text-red-600 dark:text-red-400">{{ matrixStore.error }}</div>

    <!-- Mobile hint: matrix stays a scrollable table, unlike other views -->
    <p
      v-if="!matrixStore.loading && !matrixStore.error"
      class="sm:hidden text-xs text-gray-400 dark:text-gray-500 mb-2 flex items-center gap-1"
    >
      ← Horizontal scrollen, um weitere Gemeinden zu sehen →
    </p>

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
import { onMounted, ref, toRef, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useSessionViewSettings, sessionField, sessionText, sessionDate } from '../composables/useSessionViewSettings'
import { useMatrixStore } from '../stores/matrix'
import { useDistrictsStore } from '../stores/districts'
import { useLeadersStore } from '../stores/leaders'
import type { MatrixCell } from '../api/matrix'
import MatrixFilters from '../components/MatrixFilters.vue'
import MatrixTable from '../components/MatrixTable.vue'
import AssignmentModal from '../components/AssignmentModal.vue'
import MonthlyReleaseDialog from '../components/MonthlyReleaseDialog.vue'
import MatrixSkeleton from '../components/MatrixSkeleton.vue'
import ContextualHelp from '../components/ContextualHelp.vue'
import { useToast } from '../composables/useToast'

const matrixStore = useMatrixStore()
const districtsStore = useDistrictsStore()
const leadersStore = useLeadersStore()
const toast = useToast()

const COMPACT_MODE_STORAGE_KEY = 'matrix.compactMode'
const compactMode = ref(false)
const matrixSortMode = ref<'default' | 'grouped'>('default')
const showReleaseDialog = ref(false)
const auth = useAuthStore()
useSessionViewSettings('matrix', () => auth.user?.sub ?? null, () => districtsStore.selectedDistrictId, {
  group: sessionField(toRef(matrixStore, 'groupId'), () => '', sessionText),
  query: sessionField(toRef(matrixStore, 'congregationQuery'), () => '', sessionText),
  from: sessionField(toRef(matrixStore, 'fromDt'), () => monthRange(0).from, sessionDate),
  to: sessionField(toRef(matrixStore, 'toDt'), () => monthRange(0).to, sessionDate),
  sort: sessionField(matrixSortMode, () => 'default', (value) => value === 'default' || value === 'grouped'),
})

function validateGroup() {
  if (matrixStore.groupId && !districtsStore.groups.some((group) => group.id === matrixStore.groupId)) {
    matrixStore.groupId = ''
  }
}

function onReleaseComplete(count: number) {
  showReleaseDialog.value = false
  toast.success('Freigabe abgeschlossen', `${count} Termin${count === 1 ? '' : 'e'} bestätigt.`)
  matrixStore.fetch() // refresh matrix after release
}

function setCompactMode(enabled: boolean) {
  compactMode.value = enabled
  localStorage.setItem(COMPACT_MODE_STORAGE_KEY, enabled ? '1' : '0')
}

function onSortModeChange(value: 'default' | 'grouped') {
  matrixSortMode.value = value
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  compactMode.value = localStorage.getItem(COMPACT_MODE_STORAGE_KEY) === '1'
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
    validateGroup()
    matrixStore.fetch()
  }
})

async function onDistrictChange() {
  matrixStore.districtId = districtsStore.selectedDistrictId
  matrixStore.matrix = null
  const districtId = matrixStore.districtId
  if (districtId) {
    await Promise.allSettled([
      districtsStore.fetchGroups(matrixStore.districtId),
      districtsStore.fetchCongregations(matrixStore.districtId),
      leadersStore.fetchLeaders(matrixStore.districtId),
    ])
    if (districtId !== districtsStore.selectedDistrictId) return
    validateGroup()
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
