<template>
  <div v-if="open" class="modal-backdrop" @click.self="cancel">
    <div class="modal-panel max-w-sm">
      <div class="flex items-center justify-between mb-1">
        <h2 class="modal-title">Monatsfreigabe</h2>
        <button class="modal-close" @click="cancel">
          <XMarkIcon class="h-5 w-5" />
        </button>
      </div>

      <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
        Bestätigen Sie alle geplanten Termine für einen Monat auf einmal.
      </p>

      <div class="space-y-3">
        <div>
          <label class="filter-label">Monat</label>
          <select v-model="selectedMonth" class="form-select w-full">
            <option
              v-for="m in availableMonths"
              :key="m.value"
              :value="m.value"
            >
              {{ m.label }}
            </option>
          </select>
        </div>

        <div
          v-if="plannedCount !== null"
          class="text-sm rounded px-3 py-2"
          :class="plannedCount > 0
            ? 'bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-300'
            : 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300'"
        >
          <template v-if="plannedCount > 0">
            {{ plannedCount }} Termin{{ plannedCount === 1 ? '' : 'e' }} in diesem Monat noch geplant.
          </template>
          <template v-else>
            Alle Termine in diesem Monat sind bereits bestätigt.
          </template>
        </div>
      </div>

      <div class="flex justify-end gap-2 mt-6">
        <button class="btn-secondary px-4 py-2 text-sm" @click="cancel">
          Abbrechen
        </button>
        <button
          class="btn-primary px-4 py-2 text-sm disabled:opacity-50"
          :disabled="!selectedMonth || submitting || plannedCount === 0"
          @click="confirmRelease"
        >
          <template v-if="submitting">Wird ausgeführt…</template>
          <template v-else>Alle bestätigen</template>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'
import { bulkUpdateApprovalStatus, listEvents } from '../api/events'
import type { EventResponse } from '../api/events'

const props = defineProps<{
  open: boolean
  districtId: string
}>()

const emit = defineEmits<{
  close: []
  released: [count: number]
}>()

const selectedMonth = ref('')
const submitting = ref(false)
const plannedCount = ref<number | null>(null)

const MONTH_NAMES = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
]

const now = new Date()
const availableMonths = computed(() => {
  const months: { value: string; label: string }[] = []
  for (let i = -1; i <= 3; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() + i, 1)
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    months.push({
      value,
      label: `${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`,
    })
  }
  return months
})

// When dialog opens, default to current month
watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      selectedMonth.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
      submitted.value = false
      await countPlanned()
    }
  },
)

// Local flag to prevent showing count after successful release
const submitted = ref(false)

async function countPlanned() {
  if (!selectedMonth.value) return
  const [year, month] = selectedMonth.value.split('-').map(Number)
  const fromDt = new Date(year, month - 1, 1)
  const toDt = new Date(year, month, 0, 23, 59, 59)
  try {
    const res = await listEvents({
      district_id: props.districtId,
      approval_status: 'PLANNED',
      from_dt: fromDt.toISOString(),
      to_dt: toDt.toISOString(),
      limit: 1,
      offset: 0,
    })
    plannedCount.value = res.total
  } catch {
    plannedCount.value = 0
  }
}

watch(selectedMonth, () => {
  if (props.open && !submitted.value) {
    countPlanned()
  }
})

async function confirmRelease() {
  if (!selectedMonth.value) return
  const [year, month] = selectedMonth.value.split('-').map(Number)
  submitting.value = true
  try {
    const res = await bulkUpdateApprovalStatus(props.districtId, {
      year,
      month,
      approval_status: 'CONFIRMED',
    })
    submitted.value = true
    emit('released', res.updated_count)
  } catch (e) {
    // error handling - could show toast
    console.error('Freigabe fehlgeschlagen:', e)
  } finally {
    submitting.value = false
  }
}

function cancel() {
  emit('close')
}
</script>
