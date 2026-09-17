<template>
  <section class="mt-10 border-t border-gray-200 pt-6 dark:border-gray-700">
    <div class="mb-3 flex items-center justify-between gap-3">
      <div>
        <h2 class="text-base font-semibold text-gray-800 dark:text-gray-200">Abwesenheiten</h2>
        <p class="text-xs text-gray-500 dark:text-gray-400">Urlaub und Sperrzeiten für die Dienstplanung.</p>
      </div>
      <button class="btn-secondary" :disabled="loading" @click="load">
        Aktualisieren
      </button>
    </div>

    <form class="mb-5 grid gap-3 rounded-lg border border-gray-200 p-4 dark:border-gray-700 sm:grid-cols-2" @submit.prevent="submit">
      <label class="form-label">
        Amtstragende:r
        <select v-model="form.leaderId" class="form-select mt-1 w-full" required>
          <option value="">Bitte auswählen…</option>
          <option v-for="leader in leaders" :key="leader.id" :value="leader.id">
            {{ leader.rank ? `${leader.rank} ` : '' }}{{ leader.name }}
          </option>
        </select>
      </label>
      <label class="form-label">
        Grund
        <select v-model="form.reason" class="form-select mt-1 w-full">
          <option value="URLAUB">Urlaub</option>
          <option value="SPERRZEIT">Sperrzeit</option>
          <option value="FORTBILDUNG">Fortbildung</option>
          <option value="SONSTIGES">Sonstiges</option>
        </select>
      </label>
      <label class="form-label">
        Beginn
        <input v-model="form.startAt" class="form-input mt-1 w-full" type="datetime-local" required />
      </label>
      <label class="form-label">
        Ende
        <input v-model="form.endAt" class="form-input mt-1 w-full" type="datetime-local" required />
      </label>
      <label class="form-label sm:col-span-2">
        Notiz
        <input v-model="form.note" class="form-input mt-1 w-full" maxlength="2000" type="text" />
      </label>
      <div class="flex items-end justify-end sm:col-span-2">
        <button class="btn-primary" type="submit" :disabled="saving || !form.leaderId">
          {{ saving ? 'Speichern…' : 'Abwesenheit speichern' }}
        </button>
      </div>
      <p v-if="error" class="text-sm text-red-600 sm:col-span-2" role="alert">{{ error }}</p>
    </form>

    <div v-if="loading" class="text-sm text-gray-500">Lade Abwesenheiten…</div>
    <div v-else-if="items.length === 0" class="text-sm text-gray-500">Keine Abwesenheiten erfasst.</div>
    <div v-else class="card overflow-hidden">
      <div class="table-scroll">
        <table class="table-min-w w-full text-sm">
          <thead class="table-thead">
            <tr>
              <th class="table-th">Amtstragende:r</th>
              <th class="table-th">Zeitraum</th>
              <th class="table-th">Grund</th>
              <th class="table-th">Notiz</th>
              <th class="table-th text-right">Aktion</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            <tr v-for="item in items" :key="item.id">
              <td class="table-td">{{ leaderName(item.leader_id) }}</td>
              <td class="table-td whitespace-nowrap">{{ formatPeriod(item.start_at, item.end_at) }}</td>
              <td class="table-td">{{ reasonLabel(item.reason) }}</td>
              <td class="table-td">{{ item.note || '—' }}</td>
              <td class="table-td text-right">
                <button class="btn-icon text-red-600" title="Abwesenheit löschen" @click="remove(item.id)">
                  <TrashIcon class="h-4 w-4" />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { TrashIcon } from '@heroicons/vue/24/outline'
import {
  createLeaderUnavailability,
  deleteLeaderUnavailability,
  listLeaderUnavailabilities,
  type LeaderUnavailabilityResponse,
  type UnavailabilityReason,
} from '../api/leaderUnavailabilities'
import type { LeaderResponse } from '../api/leaders'

const props = defineProps<{
  districtId: string
  leaders: LeaderResponse[]
}>()

const items = ref<LeaderUnavailabilityResponse[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const form = reactive({
  leaderId: '',
  startAt: '',
  endAt: '',
  reason: 'URLAUB' as UnavailabilityReason,
  note: '',
})

const labels: Record<UnavailabilityReason, string> = {
  URLAUB: 'Urlaub',
  SPERRZEIT: 'Sperrzeit',
  FORTBILDUNG: 'Fortbildung',
  SONSTIGES: 'Sonstiges',
}

async function load() {
  if (!props.districtId) return
  loading.value = true
  error.value = ''
  try {
    items.value = await listLeaderUnavailabilities(props.districtId)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Abwesenheiten konnten nicht geladen werden'
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!props.districtId || !form.leaderId) return
  error.value = ''
  if (!form.startAt || !form.endAt || new Date(form.endAt) <= new Date(form.startAt)) {
    error.value = 'Das Ende muss nach dem Beginn liegen.'
    return
  }
  saving.value = true
  try {
    await createLeaderUnavailability(props.districtId, {
      leader_id: form.leaderId,
      start_at: new Date(form.startAt).toISOString(),
      end_at: new Date(form.endAt).toISOString(),
      reason: form.reason,
      note: form.note.trim() || null,
    })
    form.startAt = ''
    form.endAt = ''
    form.note = ''
    await load()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Abwesenheit konnte nicht gespeichert werden'
  } finally {
    saving.value = false
  }
}

async function remove(id: string) {
  if (!props.districtId || !window.confirm('Abwesenheit wirklich löschen?')) return
  try {
    await deleteLeaderUnavailability(props.districtId, id)
    await load()
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Abwesenheit konnte nicht gelöscht werden'
  }
}

function leaderName(id: string): string {
  return props.leaders.find((leader) => leader.id === id)?.name ?? 'Unbekannt'
}

function reasonLabel(reason: UnavailabilityReason): string {
  return labels[reason]
}

function formatPeriod(startAt: string, endAt: string): string {
  const format = (value: string) => new Date(value).toLocaleString('de-DE', {
    dateStyle: 'short',
    timeStyle: 'short',
  })
  return `${format(startAt)} – ${format(endAt)}`
}

watch(() => props.districtId, load)
onMounted(load)
</script>
