<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-lg font-semibold text-gray-900">Ereignisse</h1>
      <span class="text-sm text-gray-400">{{ eventsStore.total }} gesamt</span>
    </div>

    <!-- Filter-Leiste -->
    <div class="bg-white rounded-lg border border-gray-200 p-4 mb-5">

      <!-- Schnellfilter -->
      <div class="flex items-center gap-2 mb-3">
        <span class="text-xs text-gray-400 font-medium mr-1">Schnellfilter:</span>
        <button
          v-for="preset in presets"
          :key="preset.key"
          class="text-xs px-3 py-1 rounded-full border transition-colors"
          :class="activePreset === preset.key
            ? 'bg-blue-600 text-white border-blue-600'
            : 'border-gray-300 text-gray-600 hover:border-blue-400 hover:text-blue-600'"
          @click="setPreset(preset.key)"
        >
          {{ preset.label }}
        </button>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">

        <!-- Bezirk -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Bezirk</label>
          <select
            v-model="selectedDistrictId"
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            @change="onDistrictChange"
          >
            <option value="">Alle Bezirke</option>
            <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">
              {{ d.name }}
            </option>
          </select>
        </div>

        <!-- Gemeinde -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Gemeinde</label>
          <select
            v-model="selectedCongregationId"
            :disabled="!selectedDistrictId"
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
            @change="applyFilters"
          >
            <option value="">Alle Gemeinden</option>
            <option v-for="c in districtsStore.congregations" :key="c.id" :value="c.id">
              {{ c.name }}
            </option>
          </select>
        </div>

        <!-- Status -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Status</label>
          <select
            v-model="selectedStatus"
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            @change="applyFilters"
          >
            <option value="">Alle</option>
            <option value="DRAFT">Entwurf</option>
            <option value="PUBLISHED">Veröffentlicht</option>
            <option value="CANCELLED">Abgesagt</option>
          </select>
        </div>

        <!-- Von -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Von</label>
          <input
            v-model="fromDate"
            type="date"
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            @change="applyFilters"
          />
        </div>

        <!-- Bis -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Bis</label>
          <input
            v-model="toDate"
            type="date"
            class="w-full rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            @change="applyFilters"
          />
        </div>

      </div>
    </div>

    <!-- Tabelle -->
    <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 uppercase tracking-wide">
            <th class="px-4 py-3 text-left">Titel</th>
            <th class="px-4 py-3 text-left">Start</th>
            <th class="px-4 py-3 text-left">Kategorie</th>
            <th class="px-4 py-3 text-left">Zuordnung</th>
            <th class="px-4 py-3 text-left">Status</th>
            <th class="px-4 py-3 text-left">Quelle</th>
            <th class="px-4 py-3 text-left"></th>
          </tr>
        </thead>
        <tbody>
          <!-- Laden -->
          <tr v-if="eventsStore.loading">
            <td colspan="7" class="px-4 py-10 text-center text-gray-400 text-sm">
              Laden…
            </td>
          </tr>

          <!-- Fehler -->
          <tr v-else-if="eventsStore.error">
            <td colspan="7" class="px-4 py-10 text-center text-red-500 text-sm">
              {{ eventsStore.error }}
            </td>
          </tr>

          <!-- Leer -->
          <tr v-else-if="eventsStore.items.length === 0">
            <td colspan="7" class="px-4 py-10 text-center text-gray-400 text-sm">
              Keine Ereignisse gefunden.
            </td>
          </tr>

          <!-- Daten -->
          <tr
            v-else
            v-for="event in eventsStore.items"
            :key="event.id"
            class="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors"
          >
            <td class="px-4 py-3 font-medium text-gray-900">{{ event.title }}</td>
            <td class="px-4 py-3 text-gray-600 whitespace-nowrap">{{ formatDt(event.start_at) }}</td>
            <td class="px-4 py-3 text-gray-600">{{ event.category ?? '—' }}</td>
            <td class="px-4 py-3 text-gray-600 text-xs">
              <span>{{ districtName(event.district_id) }}</span>
              <template v-if="event.congregation_id">
                <span class="text-gray-400"> › </span>
                <span>{{ congregationName(event.congregation_id) }}</span>
              </template>
              <span v-else class="ml-1 text-gray-400">(Bezirk)</span>
            </td>
            <td class="px-4 py-3">
              <span :class="statusClass(event.status)" class="px-2 py-0.5 rounded-full text-xs font-medium">
                {{ statusLabel(event.status) }}
              </span>
            </td>
            <td class="px-4 py-3">
              <span
                class="px-2 py-0.5 rounded-full text-xs font-medium"
                :class="event.source === 'EXTERNAL' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'"
              >
                {{ event.source === 'EXTERNAL' ? 'Import' : 'Intern' }}
              </span>
            </td>
            <td class="px-4 py-2 text-right">
              <button
                class="p-1.5 border border-gray-300 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-700"
                title="Zuordnung bearbeiten"
                @click="openEdit(event)"
              >
                <BuildingOffice2Icon class="h-4 w-4" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div
      v-if="eventsStore.totalPages > 1"
      class="mt-4 flex items-center justify-between text-sm text-gray-600"
    >
      <span>Seite {{ eventsStore.currentPage }} von {{ eventsStore.totalPages }}</span>
      <div class="flex gap-2">
        <button
          class="px-3 py-1.5 rounded border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="eventsStore.currentPage <= 1"
          @click="eventsStore.goToPage(eventsStore.currentPage - 1); eventsStore.fetch()"
        >
          ← Zurück
        </button>
        <button
          class="px-3 py-1.5 rounded border border-gray-300 text-sm hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="eventsStore.currentPage >= eventsStore.totalPages"
          @click="eventsStore.goToPage(eventsStore.currentPage + 1); eventsStore.fetch()"
        >
          Weiter →
        </button>
      </div>
    </div>

    <!-- Zuordnungs-Modal -->
    <div
      v-if="editTarget"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="editTarget = null"
    >
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <div class="flex items-center justify-between mb-1">
          <h2 class="text-base font-semibold text-gray-900">Termin zuordnen</h2>
          <button class="p-1 rounded hover:bg-gray-100 text-gray-400" @click="editTarget = null">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <p class="text-sm text-gray-500 mb-4 truncate">{{ editTarget.title }}</p>

        <div class="space-y-4">
          <!-- Bezirk -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Bezirk</label>
            <select
              v-model="editForm.district_id"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">
                {{ d.name }}
              </option>
            </select>
          </div>

          <!-- Gemeinde -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Gemeinde <span class="text-gray-400 font-normal">(leer = Bezirksebene)</span>
            </label>
            <select
              v-model="editForm.congregation_id"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Bezirksebene</option>
              <option v-for="c in editCongregations" :key="c.id" :value="c.id">
                {{ c.name }}
              </option>
            </select>
          </div>

          <!-- Status -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              v-model="editForm.status"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="DRAFT">Entwurf</option>
              <option value="PUBLISHED">Veröffentlicht</option>
              <option value="CANCELLED">Abgesagt</option>
            </select>
          </div>

          <!-- Kategorie -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Kategorie <span class="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              v-model="editForm.category"
              type="text"
              placeholder="z. B. Gottesdienst"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <p v-if="editError" class="text-sm text-red-600 mt-3">{{ editError }}</p>

        <div class="flex justify-end gap-3 mt-6">
          <button
            class="text-sm px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
            @click="editTarget = null"
          >
            Abbrechen
          </button>
          <button
            class="text-sm px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            :disabled="editSaving"
            @click="saveEdit"
          >
            {{ editSaving ? 'Speichern…' : 'Speichern' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { BuildingOffice2Icon, XMarkIcon } from '@heroicons/vue/24/outline'
import { useDistrictsStore } from '@/stores/districts'
import { useEventsStore } from '@/stores/events'
import { listCongregations, type CongregationResponse } from '@/api/districts'
import { updateEvent, type EventResponse } from '@/api/events'

const eventsStore = useEventsStore()
const districtsStore = useDistrictsStore()

const selectedDistrictId = ref('')
const selectedCongregationId = ref('')
const selectedStatus = ref('')
const fromDate = ref('')
const toDate = ref('')

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
  { key: 'all',     label: 'Alle' },
]

const activePreset = computed(() => {
  const curr = monthRange(0)
  const next = monthRange(1)
  if (fromDate.value === curr.from && toDate.value === curr.to) return 'current'
  if (fromDate.value === next.from && toDate.value === next.to) return 'next'
  if (!fromDate.value && !toDate.value) return 'all'
  return null
})

function setPreset(key: string) {
  if (key === 'current') { const r = monthRange(0); fromDate.value = r.from; toDate.value = r.to }
  else if (key === 'next') { const r = monthRange(1); fromDate.value = r.from; toDate.value = r.to }
  else { fromDate.value = ''; toDate.value = '' }
  applyFilters()
}

// Preloaded congregations for name display
const allCongregations = ref<CongregationResponse[]>([])

onMounted(async () => {
  await districtsStore.fetchDistricts()
  const all = await Promise.all(districtsStore.districts.map((d) => listCongregations(d.id)))
  allCongregations.value = all.flat()
  await eventsStore.fetch()
})

async function onDistrictChange() {
  selectedCongregationId.value = ''
  districtsStore.clearCongregations()
  if (selectedDistrictId.value) {
    await districtsStore.fetchCongregations(selectedDistrictId.value)
  }
  applyFilters()
}

function applyFilters() {
  eventsStore.setFilter({
    district_id: selectedDistrictId.value || undefined,
    congregation_id: selectedCongregationId.value || undefined,
    status: selectedStatus.value || undefined,
    from_dt: fromDate.value ? fromDate.value + 'T00:00:00' : undefined,
    to_dt: toDate.value ? toDate.value + 'T23:59:59' : undefined,
  })
  eventsStore.fetch()
}

watch(() => eventsStore.filters.offset, () => eventsStore.fetch())

function districtName(id: string): string {
  return districtsStore.districts.find((d) => d.id === id)?.name ?? id
}

function congregationName(id: string): string {
  return allCongregations.value.find((c) => c.id === id)?.name ?? id
}

function formatDt(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusLabel(s: string): string {
  return { DRAFT: 'Entwurf', PUBLISHED: 'Veröffentlicht', CANCELLED: 'Abgesagt' }[s] ?? s
}

function statusClass(s: string): string {
  return (
    {
      DRAFT: 'bg-yellow-100 text-yellow-800',
      PUBLISHED: 'bg-green-100 text-green-800',
      CANCELLED: 'bg-red-100 text-red-700',
    }[s] ?? 'bg-gray-100 text-gray-600'
  )
}

// --- Edit / Assign modal ---
const editTarget = ref<EventResponse | null>(null)
const editSaving = ref(false)
const editError = ref('')
const editCongregations = ref<CongregationResponse[]>([])

const editForm = reactive({
  district_id: '',
  congregation_id: '',
  status: 'DRAFT',
  category: '',
})

watch(() => editForm.district_id, async (id) => {
  editForm.congregation_id = ''
  try {
    editCongregations.value = id ? await listCongregations(id) : []
  } catch {
    editCongregations.value = []
  }
})

async function openEdit(event: EventResponse) {
  editTarget.value = event
  editError.value = ''
  editForm.district_id = event.district_id
  editForm.congregation_id = event.congregation_id ?? ''
  editForm.status = event.status
  editForm.category = event.category ?? ''
  editCongregations.value = []
  // Preload congregations for the event's district
  if (event.district_id) {
    listCongregations(event.district_id)
      .then((cs) => { editCongregations.value = cs })
      .catch(() => {})
  }
}

async function saveEdit() {
  if (!editTarget.value) return
  editSaving.value = true
  editError.value = ''
  try {
    const updated = await updateEvent(editTarget.value.id, {
      district_id: editForm.district_id || undefined,
      congregation_id: editForm.congregation_id || null,
      status: editForm.status || undefined,
      category: editForm.category || null,
    })
    // Update the item in the store list in-place
    const idx = eventsStore.items.findIndex((e) => e.id === updated.id)
    if (idx !== -1) eventsStore.items[idx] = updated
    editTarget.value = null
  } catch (e) {
    editError.value = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally {
    editSaving.value = false
  }
}
</script>
