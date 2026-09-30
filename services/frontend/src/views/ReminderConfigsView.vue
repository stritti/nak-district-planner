<template>
  <main class="p-6 max-w-3xl space-y-4">
    <h1 class="text-xl font-semibold">Erinnerungen konfigurieren</h1>
    <label class="block">Bezirk
      <select v-model="districtId" class="form-input">
        <option value="" disabled>Bezirk auswählen</option>
        <option v-for="district in districts" :key="district.id" :value="district.id">{{ district.name }}</option>
      </select>
    </label>
    <p v-if="loadError" role="alert" class="text-red-600">{{ loadError }}</p>
    <ReminderConfigsPanel v-if="districtId" :district-id="districtId" />
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listDistricts, type DistrictResponse } from '../api/districts'
import ReminderConfigsPanel from '../components/ReminderConfigsPanel.vue'

const districts = ref<DistrictResponse[]>([])
const districtId = ref('')
const loadError = ref<string | null>(null)
onMounted(async () => {
  try {
    districts.value = await listDistricts()
    districtId.value = districts.value[0]?.id ?? ''
  } catch (cause) {
    loadError.value = cause instanceof Error ? cause.message : 'Bezirke konnten nicht geladen werden'
  }
})
</script>
