<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <section class="space-y-4" aria-label="E-Mail-Erinnerungen">
    <h2 class="text-lg font-semibold">E-Mail-Erinnerungen</h2>
    <p class="text-sm text-gray-500">Monatliche Erinnerungen für den ausgewählten Bezirk.</p>
    <p v-if="store.error" role="alert" class="text-red-600">{{ store.error }}</p>
    <p v-if="store.loading">Erinnerungen werden geladen…</p>
    <p v-else-if="store.items.length === 0">Noch keine Erinnerungen angelegt.</p>
    <ul v-else class="space-y-2">
      <li v-for="item in store.items" :key="item.id" class="border rounded p-3 flex justify-between gap-4">
        <div>
          <strong>{{ item.subject_template }}</strong>
          <p class="text-sm text-gray-500">Am {{ item.day_of_month }}. um {{ item.time_of_day }} Uhr · {{ item.recipient_role }}</p>
        </div>
        <div class="flex gap-2 items-center">
          <button type="button" class="btn-secondary" @click="edit(item)">Bearbeiten</button>
          <label class="flex items-center gap-1 text-sm">
            <input type="checkbox" :checked="item.is_active" :disabled="store.saving" @change="toggle(item)" />
            Aktiv
          </label>
        </div>
      </li>
    </ul>
    <form class="space-y-3 border rounded p-3" @submit.prevent="save">
      <h3 class="font-medium">{{ editingId ? 'Erinnerung bearbeiten' : 'Erinnerung hinzufügen' }}</h3>
      <div class="flex gap-3">
        <label>Tag <input v-model.number="form.day_of_month" type="number" min="1" max="31" required class="form-input w-20" /></label>
        <label>Uhrzeit <input v-model="form.time_of_day" type="time" required class="form-input" /></label>
      </div>
      <label class="block">Betreff <input v-model="form.subject_template" maxlength="500" required class="form-input w-full" /></label>
      <label class="block">Nachricht <textarea v-model="form.body_template" maxlength="20000" required class="form-input w-full" /></label>
      <label class="block">Empfängerrolle
        <select v-model="form.recipient_role" class="form-input">
          <option value="PLANNER">Planer</option>
          <option value="DISTRICT_ADMIN">Bezirksadministrator</option>
          <option value="CONGREGATION_ADMIN">Gemeindeadministrator (Bezirkszuordnung)</option>
          <option value="VIEWER">Leser</option>
        </select>
      </label>
      <p class="text-xs text-gray-500">Platzhalter: {district_name}, {month}, {year}, {day}</p>
      <div class="flex gap-2">
        <button type="submit" :disabled="store.saving" class="btn-primary">{{ store.saving ? 'Speichert…' : 'Speichern' }}</button>
        <button v-if="editingId" type="button" class="btn-secondary" @click="reset">Abbrechen</button>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useReminderConfigsStore } from '../stores/reminderConfigs'
import type { ReminderConfig, ReminderConfigInput } from '../api/reminderConfigs'

const props = defineProps<{ districtId: string }>()
const store = useReminderConfigsStore()
const editingId = ref<string | null>(null)
const defaults = (): ReminderConfigInput => ({
  day_of_month: 10,
  time_of_day: '10:00',
  subject_template: '',
  body_template: '',
  recipient_role: 'PLANNER',
  is_active: true,
})
const form = reactive<ReminderConfigInput>(defaults())

function reset() {
  editingId.value = null
  Object.assign(form, defaults())
}
function edit(item: ReminderConfig) {
  editingId.value = item.id
  Object.assign(form, {
    day_of_month: item.day_of_month,
    time_of_day: item.time_of_day.slice(0, 5),
    subject_template: item.subject_template,
    body_template: item.body_template,
    recipient_role: item.recipient_role,
    is_active: item.is_active,
  })
}
async function save() {
  try {
    if (editingId.value) await store.update(editingId.value, { ...form })
    else await store.create({ ...form })
    reset()
  } catch { /* Error is displayed by the store. */ }
}
async function toggle(item: ReminderConfig) {
  try {
    if (item.is_active) await store.deactivate(item.id)
    else await store.update(item.id, { is_active: true })
  } catch { /* Error is displayed by the store. */ }
}
watch(() => props.districtId, id => { reset(); void store.load(id) })
onMounted(() => { void store.load(props.districtId) })
</script>
