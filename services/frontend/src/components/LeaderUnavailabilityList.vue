<template>
  <div class="space-y-3">
    <div class="flex flex-col sm:flex-row gap-2 sm:items-center">
      <label class="filter-label shrink-0" for="unavailability-leader-filter">Amtsträger:in</label>
      <select
        id="unavailability-leader-filter"
        v-model="selectedLeaderId"
        class="form-select"
        data-testid="unavailability-filter-select"
      >
        <option value="">Alle</option>
        <option v-for="leader in leaders" :key="leader.id" :value="leader.id">
          {{ leaderDisplayName(leader) }}
        </option>
      </select>
    </div>

    <div v-if="loading" class="text-sm text-gray-500 dark:text-gray-400">Lade Abwesenheiten…</div>
    <div v-else-if="filtered.length === 0" class="text-sm text-gray-400 dark:text-gray-500">
      Keine Abwesenheiten erfasst.
    </div>
    <div v-else class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      <div class="table-scroll">
        <table class="w-full text-sm" data-testid="unavailability-table">
          <thead class="table-thead">
            <tr>
              <th class="table-th py-2">Amtsträger:in</th>
              <th class="table-th py-2">Zeitraum</th>
              <th class="table-th py-2">Grund</th>
              <th class="table-th py-2">Notiz</th>
              <th class="table-th py-2 text-right">Aktionen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            <tr v-for="item in filtered" :key="item.id" class="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td class="table-td py-2 font-medium text-gray-800 dark:text-gray-200">{{ leaderNameFromId(item.leader_id, leaders) }}</td>
              <td class="table-td py-2">{{ formatUnavailabilityPeriod(item) }}</td>
              <td class="table-td py-2">
                <span class="badge bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300">
                  {{ unavailabilityReasonLabel(item.reason) }}
                </span>
              </td>
              <td class="table-td py-2 text-gray-500 dark:text-gray-400">{{ item.note ?? '—' }}</td>
              <td class="table-td py-2 text-right">
                <button
                  v-if="canDelete"
                  class="btn-icon hover:text-red-600 hover:bg-red-50 dark:hover:text-red-400"
                  title="Löschen"
                  aria-label="Abwesenheit löschen"
                  :data-testid="`unavailability-delete-${item.id}`"
                  @click="emit('delete', item)"
                >
                  <TrashIcon class="h-4 w-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TrashIcon } from '@heroicons/vue/24/outline'
import {
  formatUnavailabilityPeriod,
  unavailabilityReasonLabel,
  type LeaderUnavailabilityResponse,
} from '../api/leaderUnavailabilities'
import { leaderDisplayName, leaderNameFromId, type LeaderResponse } from '../api/leaders'

const props = defineProps<{
  items: LeaderUnavailabilityResponse[]
  leaders: LeaderResponse[]
  loading?: boolean
  presetLeaderId?: string | null
  canDelete?: boolean
}>()

const emit = defineEmits<{
  delete: [item: LeaderUnavailabilityResponse]
  'update:filter-leader-id': [leaderId: string]
}>()

const selectedLeaderId = ref('')

watch(
  () => props.presetLeaderId,
  (value) => {
    selectedLeaderId.value = value ?? ''
  },
  { immediate: true },
)

watch(selectedLeaderId, (value) => emit('update:filter-leader-id', value))

const filtered = computed(() =>
  selectedLeaderId.value
    ? props.items.filter((item) => item.leader_id === selectedLeaderId.value)
    : props.items,
)

</script>
