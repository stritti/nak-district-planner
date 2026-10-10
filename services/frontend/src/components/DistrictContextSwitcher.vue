<template>
  <div
    v-if="auth.isAuthenticated && districts.selectedDistrict"
    class="flex min-w-0 items-center gap-2 text-sm text-gray-700 dark:text-gray-200"
    data-testid="global-district-context"
  >
    <label
      v-if="districts.canSwitchDistrict"
      for="global-district-select"
      class="text-xs font-medium text-gray-500 dark:text-gray-400 shrink-0"
    >Bezirk</label>
    <select
      v-if="districts.canSwitchDistrict"
      id="global-district-select"
      class="form-select max-w-44 sm:max-w-60 text-sm"
      :value="districts.selectedDistrictId"
      aria-label="Aktiven Bezirk wechseln"
      @change="onDistrictChange"
    >
      <option v-for="district in districts.districts" :key="district.id" :value="district.id">
        {{ district.name }}
      </option>
    </select>
    <span
      v-else
      class="truncate max-w-40 sm:max-w-60 font-medium"
      :title="districts.selectedDistrict.name"
      :aria-label="'Aktueller Bezirk: ' + districts.selectedDistrict.name"
    >{{ districts.selectedDistrict.name }}</span>
  </div>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'

const auth = useAuthStore()
const districts = useDistrictsStore()

// The header owns initial context loading, including direct visits to any view.
watch(
  () => [auth.isAuthenticated, auth.user?.sub] as const,
  ([authenticated, identity]) => {
    if (authenticated && identity) {
      void districts.fetchDistricts().catch(() => {
        // Views continue to render their API errors; no stale district remains selected.
      })
    }
  },
  { immediate: true },
)

function onDistrictChange(event: Event) {
  districts.setSelectedDistrict((event.target as HTMLSelectElement).value)
}
</script>
