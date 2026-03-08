<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-5">
      <div class="flex items-center gap-3">
        <h1 class="text-lg font-semibold text-gray-900">Ereignisse</h1>
        <span v-if="viewMode === 'list'" class="text-sm text-gray-400">{{ eventsStore.total }} gesamt</span>
      </div>
      <!-- View toggle -->
      <div class="flex rounded-lg border border-gray-300 overflow-hidden text-sm">
        <button
          v-for="m in VIEW_MODES"
          :key="m.key"
          class="px-3 py-1.5 transition-colors"
          :class="viewMode === m.key
            ? 'bg-blue-600 text-white'
            : 'text-gray-600 hover:bg-gray-50'"
          @click="setViewMode(m.key)"
        >
          {{ m.label }}
        </button>
      </div>
    </div>

    <!-- Filter-Leiste -->
    <div class="bg-white rounded-lg border border-gray-200 p-4 mb-5">

      <!-- Zeile 1: Schnellfilter (Liste) oder Perioden-Navigation (Woche/Monat) -->
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <template v-if="viewMode === 'list'">
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
          </template>
          <template v-else>
            <button
              class="p-1.5 rounded border border-gray-300 hover:bg-gray-50 text-gray-600"
              @click="prevPeriod"
            >
              <ChevronLeftIcon class="h-4 w-4" />
            </button>
            <span class="text-sm font-medium text-gray-800 min-w-[160px] text-center">
              {{ periodLabel }}
            </span>
            <button
              class="p-1.5 rounded border border-gray-300 hover:bg-gray-50 text-gray-600"
              @click="nextPeriod"
            >
              <ChevronRightIcon class="h-4 w-4" />
            </button>
            <button
              class="text-xs px-3 py-1 rounded-full border border-gray-300 text-gray-600 hover:border-blue-400 hover:text-blue-600"
              @click="goToToday"
            >
              Heute
            </button>
          </template>
        </div>
      </div>

      <!-- Zeile 2: Filter-Felder -->
      <div class="flex flex-wrap gap-3">
        <!-- Bezirk -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Bezirk</label>
          <select
            v-model="selectedDistrictId"
            class="rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
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
            class="rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
            @change="onFilterChange"
          >
            <option value="">Alle Gemeinden</option>
            <option value="DISTRICT_ONLY">Nur Bezirksebene</option>
            <option v-for="c in districtsStore.congregations" :key="c.id" :value="c.id">
              {{ c.name }}
            </option>
          </select>
        </div>

        <!-- Gruppe -->
        <div v-if="districtsStore.groups.length > 0">
          <label class="block text-xs font-medium text-gray-500 mb-1">Gruppe (optional)</label>
          <select
            v-model="selectedGroupId"
            class="rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            @change="onGroupChange"
          >
            <option value="">Alle Gruppen</option>
            <option v-for="g in districtsStore.groups" :key="g.id" :value="g.id">
              {{ g.name }}
            </option>
          </select>
        </div>

        <!-- Status -->
        <div>
          <label class="block text-xs font-medium text-gray-500 mb-1">Status</label>
          <select
            v-model="selectedStatus"
            class="rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
            @change="onFilterChange"
          >
            <option value="">Alle</option>
            <option value="DRAFT">Entwurf</option>
            <option value="PUBLISHED">Veröffentlicht</option>
            <option value="CANCELLED">Abgesagt</option>
          </select>
        </div>

        <!-- Datumsfelder: nur in der Listenansicht -->
        <template v-if="viewMode === 'list'">
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">Von</label>
            <input
              v-model="fromDate"
              type="date"
              class="rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
              @change="applyFilters"
            />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-500 mb-1">Bis</label>
            <input
              v-model="toDate"
              type="date"
              class="rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
              @change="applyFilters"
            />
          </div>
        </template>
      </div>
    </div>

    <!-- ── Listenansicht ───────────────────────────────────────────────────── -->
    <template v-if="viewMode === 'list'">
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
            <tr v-if="eventsStore.loading">
              <td colspan="7" class="px-4 py-10 text-center text-gray-400 text-sm">Laden…</td>
            </tr>
            <tr v-else-if="eventsStore.error">
              <td colspan="7" class="px-4 py-10 text-center text-red-500 text-sm">{{ eventsStore.error }}</td>
            </tr>
            <tr v-else-if="eventsStore.items.length === 0">
              <td colspan="7" class="px-4 py-10 text-center text-gray-400 text-sm">Keine Ereignisse gefunden.</td>
            </tr>
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
    </template>

    <!-- ── Wochenansicht ──────────────────────────────────────────────────── -->
    <template v-else-if="viewMode === 'week'">
      <div class="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        <div v-if="calendarLoading" class="py-12 text-center text-sm text-gray-400">Laden…</div>
        <div v-else class="grid grid-cols-7 divide-x divide-gray-200 min-w-[700px]">
          <div v-for="day in weekDays" :key="day.iso" class="min-w-[100px]">
            <!-- Spaltenkopf -->
            <div
              class="px-2 py-2 text-center border-b border-gray-200 text-xs font-medium"
              :class="day.isToday ? 'bg-blue-600 text-white' : 'bg-gray-50 text-gray-600'"
            >
              <div>{{ day.weekdayShort }}</div>
              <div class="text-base font-semibold" :class="day.isToday ? 'text-white' : 'text-gray-900'">
                {{ day.day }}
              </div>
            </div>
            <!-- Events -->
            <div class="p-1.5 space-y-1 min-h-[140px]">
              <!-- Feiertage oben im Inhaltsbereich (wie in der Monatsansicht) -->
              <template v-if="calendarHolidays[day.iso]?.length">
                <div
                  v-for="name in calendarHolidays[day.iso]"
                  :key="name"
                  class="rounded px-1.5 py-1 text-xs leading-tight bg-amber-100 text-amber-800 font-medium"
                >{{ name }}</div>
              </template>
              <!-- Reguläre Events -->
              <template v-if="eventsByDate[day.iso]?.filter(e => e.category !== 'Feiertag').length">
                <div
                  v-for="event in eventsByDate[day.iso].filter(e => e.category !== 'Feiertag')"
                  :key="event.id"
                  class="rounded px-1.5 py-1 text-xs leading-tight cursor-pointer hover:opacity-80"
                  :class="eventPillClass(event)"
                  @click="openEdit(event)"
                >
                  <div class="font-medium truncate">{{ event.title }}</div>
                  <div class="text-[10px] opacity-70">{{ formatTime(event.start_at) }}</div>
                </div>
              </template>
              <div
                v-if="!calendarHolidays[day.iso]?.length && !eventsByDate[day.iso]?.filter(e => e.category !== 'Feiertag').length"
                class="text-gray-200 text-xs text-center pt-4"
              >–</div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Monatsansicht ──────────────────────────────────────────────────── -->
    <template v-else-if="viewMode === 'month'">
      <div class="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        <!-- Wochentag-Header -->
        <div class="grid grid-cols-7 divide-x divide-gray-200 border-b border-gray-200 bg-gray-50 min-w-[560px]">
          <div
            v-for="wd in WEEKDAY_LABELS"
            :key="wd"
            class="py-2 text-center text-xs font-medium text-gray-500"
          >
            {{ wd }}
          </div>
        </div>

        <div v-if="calendarLoading" class="py-12 text-center text-sm text-gray-400">Laden…</div>
        <div v-else class="grid grid-cols-7 divide-x divide-gray-200 min-w-[560px]">
          <div
            v-for="day in calendarDays"
            :key="day.iso"
            class="border-b border-gray-200 min-h-[100px] p-1"
            :class="day.currentMonth ? 'bg-white' : 'bg-gray-50'"
          >
            <!-- Tagesnummer -->
            <div class="flex items-center justify-between mb-1">
              <span
                class="inline-flex items-center justify-center w-6 h-6 text-xs font-medium rounded-full"
                :class="day.isToday
                  ? 'bg-blue-600 text-white'
                  : day.currentMonth ? 'text-gray-800' : 'text-gray-400'"
              >
                {{ day.day }}
              </span>
            </div>

            <!-- Feiertage -->
            <template v-if="calendarHolidays[day.iso]?.length">
              <div
                v-for="name in calendarHolidays[day.iso]"
                :key="name"
                class="text-[10px] leading-tight px-1 py-0.5 rounded bg-amber-100 text-amber-800 font-medium mb-0.5 truncate"
              >
                {{ name }}
              </div>
            </template>

            <!-- Events (max. 3, dann "+N weitere") -->
            <template v-if="eventsByDate[day.iso]?.filter(e => e.category !== 'Feiertag').length">
              <div
                v-for="event in eventsByDate[day.iso].filter(e => e.category !== 'Feiertag').slice(0, 3)"
                :key="event.id"
                class="text-[10px] leading-tight px-1 py-0.5 rounded mb-0.5 truncate cursor-pointer hover:opacity-80"
                :class="eventPillClass(event)"
                @click="openEdit(event)"
              >
                {{ event.title }}
              </div>
              <div
                v-if="eventsByDate[day.iso].filter(e => e.category !== 'Feiertag').length > 3"
                class="text-[10px] text-gray-400 px-1"
              >
                +{{ eventsByDate[day.iso].filter(e => e.category !== 'Feiertag').length - 3 }} weitere
              </div>
            </template>
          </div>
        </div>
      </div>
    </template>

    <!-- ── Zuordnungs-Modal (alle Ansichten) ──────────────────────────────── -->
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
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Bezirk</label>
            <select
              v-model="editForm.district_id"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">
              Gemeinde <span class="text-gray-400 font-normal">(leer = Bezirksebene)</span>
            </label>
            <select
              v-model="editForm.congregation_id"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Bezirksebene</option>
              <option v-for="c in editCongregations" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
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
import {
  BuildingOffice2Icon,
  ChevronLeftIcon,
  ChevronRightIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { useDistrictsStore } from '@/stores/districts'
import { useEventsStore } from '@/stores/events'
import { listCongregations, type CongregationResponse } from '@/api/districts'
import { listEvents, updateEvent, type EventListParams, type EventResponse } from '@/api/events'

const eventsStore = useEventsStore()
const districtsStore = useDistrictsStore()

// ── Ansichts-Modus ───────────────────────────────────────────────────────────

const VIEW_MODES = [
  { key: 'list' as const,  label: 'Liste' },
  { key: 'week' as const,  label: 'Woche' },
  { key: 'month' as const, label: 'Monat' },
]
type ViewMode = 'list' | 'week' | 'month'

const viewMode = ref<ViewMode>('list')
const currentPeriodStart = ref(new Date())
const calendarEvents = ref<EventResponse[]>([])
const calendarLoading = ref(false)

const WEEKDAY_LABELS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
const WEEKDAY_SHORT  = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
const MONTH_NAMES    = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
                        'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']

function localDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function startOfWeek(d: Date): Date {
  const r = new Date(d)
  const dow = r.getDay()
  r.setDate(r.getDate() - (dow === 0 ? 6 : dow - 1)) // Monday
  return r
}

function setViewMode(mode: ViewMode) {
  viewMode.value = mode
  if (mode === 'list') {
    applyFilters()
    return
  }
  if (mode === 'week') currentPeriodStart.value = startOfWeek(new Date())
  else currentPeriodStart.value = new Date(new Date().getFullYear(), new Date().getMonth(), 1)
  fetchCalendar()
}

function prevPeriod() {
  const d = new Date(currentPeriodStart.value)
  if (viewMode.value === 'week') d.setDate(d.getDate() - 7)
  else d.setMonth(d.getMonth() - 1)
  currentPeriodStart.value = d
  fetchCalendar()
}

function nextPeriod() {
  const d = new Date(currentPeriodStart.value)
  if (viewMode.value === 'week') d.setDate(d.getDate() + 7)
  else d.setMonth(d.getMonth() + 1)
  currentPeriodStart.value = d
  fetchCalendar()
}

function goToToday() {
  if (viewMode.value === 'week') currentPeriodStart.value = startOfWeek(new Date())
  else currentPeriodStart.value = new Date(new Date().getFullYear(), new Date().getMonth(), 1)
  fetchCalendar()
}

async function fetchCalendar() {
  calendarLoading.value = true
  try {
    let from: string, to: string
    if (viewMode.value === 'week') {
      const end = new Date(currentPeriodStart.value)
      end.setDate(end.getDate() + 6)
      from = localDate(currentPeriodStart.value) + 'T00:00:00'
      to   = localDate(end) + 'T23:59:59'
    } else {
      // Monatsansicht: komplettes Kalender-Grid (bis zu 6 Wochen)
      const year = currentPeriodStart.value.getFullYear()
      const month = currentPeriodStart.value.getMonth()
      const firstDay = new Date(year, month, 1)
      const dow = firstDay.getDay()
      const gridStart = new Date(firstDay)
      gridStart.setDate(gridStart.getDate() - (dow === 0 ? 6 : dow - 1))
      const gridEnd = new Date(gridStart)
      gridEnd.setDate(gridEnd.getDate() + 41)
      from = localDate(gridStart) + 'T00:00:00'
      to   = localDate(gridEnd)   + 'T23:59:59'
    }
    const params: EventListParams = { from_dt: from, to_dt: to, limit: 500, offset: 0 }
    if (selectedDistrictId.value)     params.district_id     = selectedDistrictId.value
    if (selectedCongregationId.value === 'DISTRICT_ONLY') {
      params.only_district_level = true
    } else if (selectedCongregationId.value) {
      params.congregation_id = selectedCongregationId.value
    }
    if (selectedGroupId.value)        params.group_id        = selectedGroupId.value
    if (selectedStatus.value)         params.status          = selectedStatus.value
    const res = await listEvents(params)
    let events = res.items

    // Bei Gemeinde-Filter: Feiertage des Bezirks zusätzlich laden (keine congregation_id-Einschränkung)
    if (selectedCongregationId.value && selectedDistrictId.value) {
      const feierRes = await listEvents({ district_id: selectedDistrictId.value, from_dt: from, to_dt: to, limit: 500, offset: 0 })
      const existing = new Set(events.map(e => e.id))
      const feiertage = feierRes.items.filter(e => e.category === 'Feiertag' && !existing.has(e.id))
      events = [...events, ...feiertage]
    }

    calendarEvents.value = events
  } catch {
    calendarEvents.value = []
  } finally {
    calendarLoading.value = false
  }
}

// ── Kalender-Berechnungen ────────────────────────────────────────────────────

const weekDays = computed(() => {
  const today = localDate(new Date())
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(currentPeriodStart.value)
    d.setDate(d.getDate() + i)
    return {
      iso:         localDate(d),
      day:         d.getDate(),
      weekdayShort: WEEKDAY_SHORT[d.getDay()],
      isToday:     localDate(d) === today,
    }
  })
})

const calendarDays = computed(() => {
  const year  = currentPeriodStart.value.getFullYear()
  const month = currentPeriodStart.value.getMonth()
  const firstDay = new Date(year, month, 1)
  const dow = firstDay.getDay()
  const start = new Date(firstDay)
  start.setDate(start.getDate() - (dow === 0 ? 6 : dow - 1))
  const today = localDate(new Date())
  return Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start)
    d.setDate(d.getDate() + i)
    return {
      iso:          localDate(d),
      day:          d.getDate(),
      currentMonth: d.getMonth() === month,
      isToday:      localDate(d) === today,
    }
  })
})

const eventsByDate = computed(() => {
  const map: Record<string, EventResponse[]> = {}
  for (const event of calendarEvents.value) {
    const key = event.start_at.slice(0, 10)
    if (!map[key]) map[key] = []
    map[key].push(event)
  }
  for (const key in map) {
    map[key].sort((a, b) => a.start_at.localeCompare(b.start_at))
  }
  return map
})

// Feiertage separat, damit sie im Spaltenkopf erscheinen (nicht im Event-Bereich)
const calendarHolidays = computed(() => {
  const map: Record<string, string[]> = {}
  for (const event of calendarEvents.value) {
    if (event.category === 'Feiertag') {
      const key = event.start_at.slice(0, 10)
      if (!map[key]) map[key] = []
      map[key].push(event.title)
    }
  }
  return map
})

const periodLabel = computed(() => {
  if (viewMode.value === 'week' && weekDays.value.length) {
    const s = weekDays.value[0].iso
    const e = weekDays.value[6].iso
    const fmt = (iso: string) => iso.slice(8) + '.' + iso.slice(5, 7) + '.'
    return `${fmt(s)} – ${fmt(e)}${e.slice(0, 4)}`
  }
  const m = currentPeriodStart.value.getMonth()
  const y = currentPeriodStart.value.getFullYear()
  return `${MONTH_NAMES[m]} ${y}`
})

// ── Filter ───────────────────────────────────────────────────────────────────

const selectedDistrictId    = ref('')
const selectedCongregationId = ref('')
const selectedGroupId        = ref('')
const selectedStatus         = ref('')
const fromDate               = ref('')
const toDate                 = ref('')

function monthRange(offset: number) {
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

async function onDistrictChange() {
  selectedCongregationId.value = ''
  selectedGroupId.value = ''
  districtsStore.clearCongregations()
  if (selectedDistrictId.value) {
    await Promise.all([
      districtsStore.fetchCongregations(selectedDistrictId.value),
      districtsStore.fetchGroups(selectedDistrictId.value),
    ])
  }
  onFilterChange()
}

function onGroupChange() {
  selectedCongregationId.value = ''
  onFilterChange()
}

function onFilterChange() {
  if (viewMode.value === 'list') applyFilters()
  else fetchCalendar()
}

function applyFilters() {
  const isDistrictOnly = selectedCongregationId.value === 'DISTRICT_ONLY'
  eventsStore.setFilter({
    district_id:    selectedDistrictId.value || undefined,
    congregation_id: (!isDistrictOnly && selectedCongregationId.value) ? selectedCongregationId.value : undefined,
    group_id:        selectedGroupId.value || undefined,
    only_district_level: isDistrictOnly,
    status:          selectedStatus.value || undefined,
    from_dt: fromDate.value ? fromDate.value + 'T00:00:00' : undefined,
    to_dt:   toDate.value   ? toDate.value   + 'T23:59:59' : undefined,
  })
  eventsStore.fetch()
}

// ── Lifecycle ────────────────────────────────────────────────────────────────

const allCongregations = ref<CongregationResponse[]>([])

onMounted(async () => {
  await districtsStore.fetchDistricts()
  const all = await Promise.all(districtsStore.districts.map((d) => listCongregations(d.id)))
  allCongregations.value = all.flat()
  await eventsStore.fetch()
})

watch(() => eventsStore.filters.offset, () => eventsStore.fetch())

// ── Hilfsfunktionen ──────────────────────────────────────────────────────────

function districtName(id: string): string {
  return districtsStore.districts.find((d) => d.id === id)?.name ?? id
}

function congregationName(id: string): string {
  return allCongregations.value.find((c) => c.id === id)?.name ?? id
}

function formatDt(iso: string): string {
  return new Date(iso).toLocaleDateString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return h === '00' && m === '00' ? '' : `${h}:${m}`
}

function statusLabel(s: string): string {
  return { DRAFT: 'Entwurf', PUBLISHED: 'Veröffentlicht', CANCELLED: 'Abgesagt' }[s] ?? s
}

function statusClass(s: string): string {
  return { DRAFT: 'bg-yellow-100 text-yellow-800', PUBLISHED: 'bg-green-100 text-green-800', CANCELLED: 'bg-red-100 text-red-700' }[s] ?? 'bg-gray-100 text-gray-600'
}

function eventPillClass(event: EventResponse): string {
  if (event.category === 'Feiertag')   return 'bg-amber-100 text-amber-800'
  if (event.status === 'CANCELLED')    return 'bg-red-100 text-red-600 line-through'
  if (event.category === 'Gottesdienst') return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-700'
}

// ── Edit-Modal ───────────────────────────────────────────────────────────────

const editTarget       = ref<EventResponse | null>(null)
const editSaving       = ref(false)
const editError        = ref('')
const editCongregations = ref<CongregationResponse[]>([])

const editForm = reactive({ district_id: '', congregation_id: '', status: 'DRAFT', category: '' })

watch(() => editForm.district_id, async (id) => {
  editForm.congregation_id = ''
  try { editCongregations.value = id ? await listCongregations(id) : [] } catch { editCongregations.value = [] }
})

async function openEdit(event: EventResponse) {
  editTarget.value = event
  editError.value  = ''
  editForm.district_id     = event.district_id
  editForm.congregation_id = event.congregation_id ?? ''
  editForm.status          = event.status
  editForm.category        = event.category ?? ''
  editCongregations.value  = []
  if (event.district_id) listCongregations(event.district_id).then(cs => { editCongregations.value = cs }).catch(() => {})
}

async function saveEdit() {
  if (!editTarget.value) return
  editSaving.value = true
  editError.value  = ''
  try {
    const updated = await updateEvent(editTarget.value.id, {
      district_id:     editForm.district_id || undefined,
      congregation_id: editForm.congregation_id || null,
      status:          editForm.status || undefined,
      category:        editForm.category || null,
    })
    // In-place update je nach aktiver Ansicht
    if (viewMode.value === 'list') {
      const idx = eventsStore.items.findIndex(e => e.id === updated.id)
      if (idx !== -1) eventsStore.items[idx] = updated
    } else {
      const idx = calendarEvents.value.findIndex(e => e.id === updated.id)
      if (idx !== -1) calendarEvents.value[idx] = updated
    }
    editTarget.value = null
  } catch (e) {
    editError.value = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally {
    editSaving.value = false
  }
}
</script>
