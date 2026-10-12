<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <section class="space-y-5" aria-labelledby="recurring-title">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 id="recurring-title" class="text-xl font-semibold text-gray-900 dark:text-gray-100">Wiederkehrende Termine</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400">Vorschläge werden erst nach ausdrücklicher Übernahme als Entwurf angelegt.</p>
      </div>
      <div class="flex gap-2" role="tablist" aria-label="Ansicht">
        <button class="btn-primary px-3 py-2 text-sm" :aria-selected="tab === 'checklist'" @click="tab = 'checklist'">Monatscheckliste</button>
        <button class="btn-primary px-3 py-2 text-sm" :aria-selected="tab === 'templates'" @click="tab = 'templates'">Vorlagen</button>
      </div>
    </div>

    <p v-if="!districtId" class="text-sm text-amber-700">Wähle einen Bezirk aus.</p>
    <template v-else>
      <p v-if="error" role="alert" class="text-sm text-red-700 dark:text-red-300">{{ error }}</p>
      <p v-if="loading" role="status" class="text-sm text-gray-500">Lade Daten…</p>

      <div v-if="tab === 'checklist'" class="space-y-4">
        <div class="card p-4 space-y-3">
          <div class="flex flex-wrap items-end gap-3">
            <div>
              <label for="recurring-month" class="filter-label">Monat</label>
              <div class="flex gap-1 items-center">
                <button aria-label="Vorheriger Monat" class="btn-icon" @click="moveMonth(-1)">‹</button>
                <input id="recurring-month" v-model="monthValue" type="month" class="form-select" />
                <button aria-label="Nächster Monat" class="btn-icon" @click="moveMonth(1)">›</button>
              </div>
            </div>
            <div>
              <label for="recurring-congregation" class="filter-label">Gemeinde</label>
              <select id="recurring-congregation" v-model="congregationFilter" class="form-select">
                <option value="">Alle berechtigten</option>
                <option v-for="congregation in districtsStore.congregations" :key="congregation.id" :value="congregation.id">{{ congregation.name }}</option>
              </select>
            </div>
            <div>
              <label for="recurring-status" class="filter-label">Entscheidung</label>
              <select id="recurring-status" v-model="statusFilter" class="form-select">
                <option value="">Alle</option>
                <option v-for="state in statuses" :key="state" :value="state">{{ statusLabel(state) }}</option>
              </select>
            </div>
            <div>
              <label for="recurring-category" class="filter-label">Kategorie</label>
              <input id="recurring-category" v-model="categoryFilter" class="form-select" placeholder="Alle Kategorien" />
            </div>
            <div class="grow">
              <label for="recurring-search" class="filter-label">Suche</label>
              <input id="recurring-search" v-model="queryFilter" class="form-select w-full" placeholder="Titel oder Beschreibung" @keyup.enter="applyFilters" />
            </div>
            <button data-testid="apply-recurring-filters" class="btn-primary px-3 py-2" :disabled="loading" @click="applyFilters">Filtern</button>
          </div>
        </div>

        <div class="flex flex-wrap gap-3 text-sm" aria-label="Planungsfortschritt">
          <span v-for="state in statuses" :key="state">{{ statusLabel(state) }}: {{ checklist.counts[state] ?? 0 }}</span>
        </div>
        <div class="flex flex-wrap justify-between gap-2 items-center">
          <p class="text-sm text-gray-500">{{ checklist.total }} Vorschläge</p>
          <button
            v-if="selectedCount > 0"
            data-testid="bulk-accept"
            class="btn-primary px-3 py-2 text-sm"
            :disabled="busy"
            @click="bulkAccept"
          >{{ selectedCount }} ausgewählte übernehmen</button>
        </div>

        <div v-if="!loading && checklist.items.length === 0" class="card p-6 text-sm text-gray-500">Keine Vorschläge für diese Auswahl.</div>
        <div class="grid gap-3 md:grid-cols-2">
          <article v-for="item in checklist.items" :key="itemKey(item)" class="card p-4 space-y-2" :data-testid="`occurrence-${item.occurrence_local_date}`">
            <div class="flex justify-between gap-2 items-start">
              <div>
                <h2 class="font-medium">{{ item.title }}</h2>
                <p class="text-sm text-gray-500">{{ item.occurrence_local_date }} · {{ item.start_time.slice(0, 5) }} Uhr · {{ item.duration_minutes }} Min.</p>
                <p class="text-xs text-gray-500">{{ item.category }}</p>
              </div>
              <span class="badge">{{ statusLabel(item.status) }}</span>
            </div>
            <p v-if="item.description" class="text-sm text-gray-600 dark:text-gray-300">{{ item.description }}</p>
            <p v-if="item.reason" class="text-sm text-amber-700">{{ item.reason }}</p>
            <p v-if="item.planning_slot_id" class="text-xs text-gray-500">Planungsslot: {{ item.planning_slot_id }}</p>
            <div v-if="canManage(item.congregation_id)" class="flex flex-wrap gap-2 items-center">
              <label v-if="item.status === 'OPEN'" class="flex gap-2 items-center text-sm">
                <input type="checkbox" :checked="selected.has(itemKey(item))" :aria-label="`${item.title} auswählen`" @change="toggleSelected(item)" />
                Auswählen
              </label>
              <button v-if="item.status === 'OPEN' || item.status === 'CONFLICT' || (item.status === 'NEEDS_REVIEW' && !item.decision_status)" class="btn-primary px-3 py-1.5 text-sm" :disabled="busy" @click="openPreview(item)">Prüfen und übernehmen</button>
              <button v-if="item.status === 'OPEN' || (item.status === 'NEEDS_REVIEW' && !item.decision_status)" class="btn-icon px-3 py-1.5 text-sm" :disabled="busy" @click="skip(item)">Auslassen</button>
              <button v-if="item.status === 'SKIPPED'" class="btn-icon px-3 py-1.5 text-sm" :disabled="busy" @click="reopen(item)">Wieder öffnen</button>
              <template v-if="item.status === 'NEEDS_REVIEW' && item.decision_status === 'ACCEPTED'">
                <button class="btn-icon px-3 py-1.5 text-sm" :disabled="busy" @click="resolve(item, 'MARK_SKIPPED')">Als ausgelassen markieren</button>
                <button class="btn-icon px-3 py-1.5 text-sm" :disabled="busy" @click="resolve(item, 'REOPEN')">Neu öffnen</button>
                <input v-model="resolveSlotId" aria-label="Slot-ID zur Zuordnung" class="form-select text-sm" placeholder="UUID des bestehenden Slots" />
                <button class="btn-primary px-3 py-1.5 text-sm" :disabled="busy || !resolveSlotId" @click="resolve(item, 'LINK_EXISTING')">Slot zuordnen</button>
              </template>
            </div>
          </article>
        </div>
        <div v-if="checklist.total > checklist.limit" class="flex items-center justify-between gap-3">
          <button class="btn-icon px-3 py-2" :disabled="loading || pageOffset === 0" @click="changePage(-1)">Zurück</button>
          <span class="text-sm">Seite {{ Math.floor(pageOffset / checklist.limit) + 1 }}</span>
          <button class="btn-icon px-3 py-2" :disabled="loading || pageOffset + checklist.limit >= checklist.total" @click="changePage(1)">Weiter</button>
        </div>
      </div>

      <div v-else class="space-y-4">
        <div class="flex items-center justify-between">
          <p class="text-sm text-gray-500">{{ templates.length }} Vorlagen</p>
          <button v-if="canCreate" data-testid="create-template" class="btn-primary px-3 py-2" @click="openNewTemplate">Vorlage anlegen</button>
        </div>
        <div class="grid gap-3 md:grid-cols-2">
          <article v-for="item in templates" :key="item.id" class="card p-4 space-y-2">
            <div class="flex justify-between gap-2">
              <h2 class="font-semibold">{{ item.title }}</h2>
              <span class="text-xs">{{ item.is_active ? 'Aktiv' : 'Inaktiv' }}</span>
            </div>
            <p class="text-sm text-gray-500">{{ item.category }} · {{ item.start_time.slice(0, 5) }} Uhr · Revision {{ item.revision }}</p>
            <p class="text-sm">{{ recurrenceLabel(item.recurrence) }}</p>
            <div v-if="canManage(item.congregation_id)" class="flex gap-2">
              <button class="btn-icon px-3 py-2 text-sm" @click="editTemplate(item)">Bearbeiten</button>
              <button v-if="item.is_active" class="btn-icon px-3 py-2 text-sm" :disabled="busy" @click="deactivateTemplate(item)">Deaktivieren</button>
            </div>
          </article>
        </div>
        <form v-if="formOpen" class="card p-4 space-y-3" data-testid="recurring-template-form" @submit.prevent="saveTemplate">
          <h2 class="font-semibold">{{ editing ? 'Vorlage bearbeiten' : 'Neue Vorlage' }}</h2>
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="text-sm">Titel<input v-model="form.title" required maxlength="500" class="form-select w-full" /></label>
            <label class="text-sm">Kategorie (kein Gottesdienst)<input v-model="form.category" required maxlength="255" class="form-select w-full" /></label>
            <label class="text-sm">Lokale Startzeit<input v-model="form.start_time" type="time" required class="form-select w-full" /></label>
            <label class="text-sm">Dauer (Minuten)<input v-model.number="form.duration_minutes" type="number" min="1" required class="form-select w-full" /></label>
            <label class="text-sm">Gemeinde
              <select v-model="form.congregation_id" class="form-select w-full" :disabled="editing !== null">
                <option v-if="districtAdmin" :value="null">Bezirkstermin</option>
                <option v-for="congregation in editableCongregations" :key="congregation.id" :value="congregation.id">{{ congregation.name }}</option>
              </select>
            </label>
            <label class="text-sm">Wiederholung
              <select v-model="form.recurrence.kind" class="form-select w-full">
                <option value="WEEKLY">Wöchentlich</option>
                <option value="MONTHLY_DAY">Monatlicher Tag</option>
                <option value="MONTHLY_WEEKDAY">Monatlicher Wochentag</option>
              </select>
            </label>
            <label class="text-sm">Ankerdatum<input v-model="form.recurrence.anchor_date" type="date" required class="form-select w-full" /></label>
            <label class="text-sm">Intervall<input v-model.number="form.recurrence.interval" type="number" min="1" required class="form-select w-full" /></label>
            <fieldset v-if="form.recurrence.kind === 'WEEKLY'" class="sm:col-span-2">
              <legend class="text-sm">Wochentage</legend>
              <label v-for="day in 7" :key="day" class="inline-flex gap-1 items-center text-sm mr-3">
                <input v-model="form.recurrence.weekdays" type="checkbox" :value="day" />
                {{ weekdays[day - 1] }}
              </label>
            </fieldset>
            <label v-if="form.recurrence.kind === 'MONTHLY_DAY'" class="text-sm">Tag des Monats
              <input v-model.number="form.recurrence.day_of_month" type="number" min="1" max="31" class="form-select w-full" />
            </label>
            <template v-if="form.recurrence.kind === 'MONTHLY_WEEKDAY'">
              <label class="text-sm">Wochentag
                <select v-model.number="form.recurrence.weekday" class="form-select w-full">
                  <option v-for="day in 7" :key="day" :value="day">{{ weekdays[day - 1] }}</option>
                </select>
              </label>
              <label class="text-sm">Vorkommen
                <select v-model.number="form.recurrence.ordinal" class="form-select w-full">
                  <option v-for="ordinal in [1, 2, 3, 4, 5, -1]" :key="ordinal" :value="ordinal">{{ ordinal === -1 ? 'Letzter' : ordinal + '.' }}</option>
                </select>
              </label>
            </template>
            <label v-if="!form.congregation_id" class="text-sm sm:col-span-2">Verteilung (all oder komma-getrennte Gemeinde-UUIDs)
              <input v-model="applicabilityInput" class="form-select w-full" placeholder="all" />
            </label>
            <label class="text-sm sm:col-span-2">Ausnahmedaten (YYYY-MM-DD, komma-getrennt)
              <input v-model="excludedDatesInput" class="form-select w-full" />
            </label>
            <label class="text-sm">Aktiv ab<input v-model="activeFromInput" type="date" class="form-select w-full" /></label>
            <label class="text-sm">Aktiv bis<input v-model="activeUntilInput" type="date" class="form-select w-full" /></label>
            <label class="text-sm sm:col-span-2">Beschreibung<textarea v-model="form.description" class="form-select w-full" rows="2" /></label>
            <label class="text-sm flex gap-2 items-center"><input v-model="form.is_active" type="checkbox" /> Aktiv</label>
          </div>
          <div class="flex gap-2">
            <button class="btn-primary px-3 py-2" type="submit" :disabled="busy">Vorlage speichern</button>
            <button class="btn-icon px-3 py-2" type="button" @click="formOpen = false">Abbrechen</button>
          </div>
        </form>
      </div>

      <form v-if="preview" data-testid="recurring-preview" class="card p-4 space-y-3" @submit.prevent="acceptPreview">
        <h2 class="font-semibold">Einzeltermin prüfen und übernehmen</h2>
        <p class="text-xs text-gray-500">Die ursprüngliche Serienzuordnung bleibt auch nach einer Verschiebung erhalten. Der Termin bleibt bis zur Monatsfreigabe PLANNED.</p>
        <div class="grid gap-3 sm:grid-cols-2">
          <label class="text-sm">Titel<input v-model="previewTitle" required class="form-select w-full" /></label>
          <label class="text-sm">Datum<input v-model="previewDate" type="date" required class="form-select w-full" /></label>
          <label class="text-sm">Uhrzeit<input v-model="previewTime" type="time" required class="form-select w-full" /></label>
          <label class="text-sm">Dauer<input v-model.number="previewDuration" type="number" min="1" required class="form-select w-full" /></label>
          <label class="text-sm sm:col-span-2">Beschreibung<textarea v-model="previewDescription" class="form-select w-full" rows="2" /></label>
          <label class="text-sm">Sommerzeit-Überlappung
            <select v-model="previewFold" class="form-select w-full">
              <option :value="null">Keine explizite Wahl</option>
              <option :value="0">Erste Uhrzeit</option>
              <option :value="1">Zweite Uhrzeit</option>
            </select>
          </label>
        </div>
        <div class="flex gap-2">
          <button type="submit" class="btn-primary px-3 py-2" :disabled="busy">Als Entwurf übernehmen</button>
          <button type="button" class="btn-icon px-3 py-2" @click="preview = null">Abbrechen</button>
        </div>
      </form>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  acceptRecurringOccurrence,
  bulkAcceptRecurringOccurrences,
  createRecurringTemplate,
  listRecurringChecklist,
  listRecurringTemplates,
  reopenRecurringOccurrence,
  resolveRecurringOccurrence,
  skipRecurringOccurrence,
  updateRecurringTemplate,
  type ChecklistItem,
  type ChecklistPage,
  type ChecklistStatus,
  type OccurrenceAction,
  type RecurrenceRule,
  type RecurringTemplate,
  type RecurringTemplateInput,
} from '../api/recurringEvents'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'

const authStore = useAuthStore()
const districtsStore = useDistrictsStore()
const districtId = computed(() => districtsStore.selectedDistrictId)
const weekdays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
const statuses: ChecklistStatus[] = ['OPEN', 'ACCEPTED', 'SKIPPED', 'CONFLICT', 'NEEDS_REVIEW']
const emptyPage = (): ChecklistPage => ({
  items: [], total: 0, limit: 50, offset: 0,
  counts: { OPEN: 0, ACCEPTED: 0, SKIPPED: 0, CONFLICT: 0, NEEDS_REVIEW: 0 },
})
const today = new Date()
const monthValue = ref(`${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`)
const checklist = ref<ChecklistPage>(emptyPage())
const templates = ref<RecurringTemplate[]>([])
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const tab = ref<'checklist' | 'templates'>('checklist')
const congregationFilter = ref('')
const queryFilter = ref('')
const categoryFilter = ref('')
const statusFilter = ref<ChecklistStatus | ''>('')
const pageOffset = ref(0)
const selected = ref(new Set<string>())
const selectedCount = computed(() => selected.value.size)
let fetchVersion = 0

const districtAdmin = computed(() => authStore.isSuperadmin || authStore.memberships.some(
  membership => membership.scope_type === 'DISTRICT'
    && membership.scope_id === districtId.value && membership.role === 'DISTRICT_ADMIN',
))
const editableCongregations = computed(() => districtsStore.congregations.filter(
  congregation => districtAdmin.value || authStore.memberships.some(
    membership => membership.scope_type === 'CONGREGATION'
      && membership.scope_id === congregation.id && membership.role === 'CONGREGATION_ADMIN',
  ),
))
const canCreate = computed(() => districtAdmin.value || editableCongregations.value.length > 0)
function canManage(congregationId: string | null): boolean {
  return districtAdmin.value || Boolean(congregationId && editableCongregations.value.some(
    congregation => congregation.id === congregationId,
  ))
}
function statusLabel(state: ChecklistStatus): string {
  return {
    OPEN: 'Offen', ACCEPTED: 'Übernommen', SKIPPED: 'Ausgelassen',
    CONFLICT: 'Konflikt', NEEDS_REVIEW: 'Prüfung nötig',
  }[state]
}
function itemKey(item: ChecklistItem): string {
  return `${item.template_id}:${item.occurrence_local_date}`
}
function actionFor(item: ChecklistItem): OccurrenceAction {
  return {
    template_id: item.template_id,
    occurrence_local_date: item.occurrence_local_date,
    template_revision: item.template_revision,
  }
}

async function load(): Promise<void> {
  const id = districtId.value
  const request = ++fetchVersion
  if (!id) return
  const [year, month] = monthValue.value.split('-').map(Number)
  loading.value = true
  error.value = ''
  try {
    const [templateResponse, page] = await Promise.all([
      listRecurringTemplates(id),
      listRecurringChecklist(id, {
        year, month,
        congregation_id: congregationFilter.value || undefined,
        q: queryFilter.value.trim() || undefined,
        category: categoryFilter.value.trim() || undefined,
        status: statusFilter.value || undefined,
        limit: 50, offset: pageOffset.value,
      }),
    ])
    if (request !== fetchVersion || id !== districtId.value) return
    templates.value = templateResponse.items
    checklist.value = page
    selected.value = new Set()
  } catch (cause) {
    if (request === fetchVersion) error.value = String(cause)
  } finally {
    if (request === fetchVersion) loading.value = false
  }
}
function applyFilters(): void {
  pageOffset.value = 0
  void load()
}
watch(monthValue, applyFilters)
function moveMonth(direction: number): void {
  const [year, month] = monthValue.value.split('-').map(Number)
  const next = new Date(Date.UTC(year, month - 1 + direction, 1))
  monthValue.value = `${next.getUTCFullYear()}-${String(next.getUTCMonth() + 1).padStart(2, '0')}`
}
function changePage(direction: number): void {
  pageOffset.value += direction * 50
  void load()
}
function toggleSelected(item: ChecklistItem): void {
  const next = new Set(selected.value)
  const key = itemKey(item)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selected.value = next
}
async function perform(task: () => Promise<unknown>): Promise<boolean> {
  if (busy.value) return false
  busy.value = true
  error.value = ''
  try {
    await task()
    await load()
    return true
  } catch (cause) {
    error.value = String(cause)
    return false
  } finally {
    busy.value = false
  }
}
function skip(item: ChecklistItem): void {
  void perform(() => skipRecurringOccurrence(districtId.value, actionFor(item)))
}
function reopen(item: ChecklistItem): void {
  void perform(() => reopenRecurringOccurrence(districtId.value, actionFor(item)))
}
const resolveSlotId = ref('')
function resolve(item: ChecklistItem, action: 'LINK_EXISTING' | 'MARK_SKIPPED' | 'REOPEN'): void {
  void perform(() => resolveRecurringOccurrence(districtId.value, {
    ...actionFor(item), action,
    planning_slot_id: action === 'LINK_EXISTING' ? resolveSlotId.value : undefined,
  }))
}
async function bulkAccept(): Promise<void> {
  const items = checklist.value.items.filter(
    item => item.status === 'OPEN' && canManage(item.congregation_id)
      && selected.value.has(itemKey(item)),
  )
  if (!items.length) return
  await perform(async () => {
    const result = await bulkAcceptRecurringOccurrences(
      districtId.value, items.map(item => actionFor(item)),
    )
    const failed = result.results.filter(item => item.error)
    if (failed.length) throw new Error(failed.map(item => item.error).join('; '))
  })
}

const preview = ref<ChecklistItem | null>(null)
const previewTitle = ref('')
const previewDescription = ref('')
const previewDate = ref('')
const previewTime = ref('')
const previewDuration = ref(90)
const previewFold = ref<0 | 1 | null>(null)
function openPreview(item: ChecklistItem): void {
  preview.value = item
  previewTitle.value = item.title
  previewDescription.value = item.description ?? ''
  previewDate.value = item.occurrence_local_date
  previewTime.value = item.start_time.slice(0, 5)
  previewDuration.value = item.duration_minutes
  previewFold.value = null
}
async function acceptPreview(): Promise<void> {
  const item = preview.value
  if (!item) return
  const success = await perform(() => acceptRecurringOccurrence(districtId.value, {
    ...actionFor(item),
    local_date_override: previewDate.value,
    local_time_override: previewTime.value,
    title_override: previewTitle.value,
    description_override: previewDescription.value,
    duration_minutes_override: previewDuration.value,
    fold: previewFold.value,
  }))
  if (success) preview.value = null
}

function newForm(): RecurringTemplateInput {
  return {
    title: '', description: null, category: 'Musik', congregation_id: null,
    start_time: '19:30', duration_minutes: 90,
    recurrence: {
      kind: 'WEEKLY', anchor_date: `${monthValue.value}-01`,
      interval: 1, weekdays: [2], day_of_month: null, weekday: null,
      ordinal: null, version: 1,
    },
    applicability: [], excluded_dates: [],
    active_from: null, active_until: null, is_active: true,
  }
}
const editing = ref<RecurringTemplate | null>(null)
const formOpen = ref(false)
const form = ref<RecurringTemplateInput>(newForm())
const applicabilityInput = ref('')
const excludedDatesInput = ref('')
const activeFromInput = ref('')
const activeUntilInput = ref('')
function loadForm(item: RecurringTemplate | null): void {
  editing.value = item
  form.value = item ? {
    ...item,
    start_time: item.start_time.slice(0, 5),
    recurrence: { ...item.recurrence, weekdays: [...item.recurrence.weekdays] },
    applicability: [...item.applicability],
    excluded_dates: [...item.excluded_dates],
  } : newForm()
  applicabilityInput.value = form.value.applicability.join(', ')
  excludedDatesInput.value = form.value.excluded_dates.join(', ')
  activeFromInput.value = form.value.active_from ?? ''
  activeUntilInput.value = form.value.active_until ?? ''
  formOpen.value = true
}
function openNewTemplate(): void {
  loadForm(null)
  if (!districtAdmin.value) form.value.congregation_id = editableCongregations.value[0]?.id ?? null
}
function editTemplate(item: RecurringTemplate): void {
  loadForm(item)
}
function recurrenceLabel(rule: RecurrenceRule): string {
  if (rule.kind === 'WEEKLY') return `Wöchentlich, Tage ${rule.weekdays.join(', ')}, Intervall ${rule.interval}`
  if (rule.kind === 'MONTHLY_DAY') return `Monatlich am ${rule.day_of_month}., Intervall ${rule.interval}`
  return `Monatlich: ${rule.ordinal === -1 ? 'letzter' : rule.ordinal + '.'} Wochentag ${rule.weekday}`
}
function normalizeForm(): RecurringTemplateInput {
  const base = form.value
  const recurrence: RecurrenceRule = {
    ...base.recurrence,
    weekdays: base.recurrence.kind === 'WEEKLY' ? base.recurrence.weekdays : [],
    day_of_month: base.recurrence.kind === 'MONTHLY_DAY' ? Number(base.recurrence.day_of_month ?? 1) : null,
    weekday: base.recurrence.kind === 'MONTHLY_WEEKDAY' ? Number(base.recurrence.weekday ?? 2) : null,
    ordinal: base.recurrence.kind === 'MONTHLY_WEEKDAY' ? Number(base.recurrence.ordinal ?? -1) : null,
  }
  return {
    ...base, recurrence,
    applicability: base.congregation_id ? [] : applicabilityInput.value.split(',').map(v => v.trim()).filter(Boolean),
    excluded_dates: excludedDatesInput.value.split(',').map(v => v.trim()).filter(Boolean),
    active_from: activeFromInput.value || null,
    active_until: activeUntilInput.value || null,
  }
}
async function saveTemplate(): Promise<void> {
  const input = normalizeForm()
  const success = await perform(() => {
    if (editing.value) {
      const { congregation_id: _congregationId, ...changes } = input
      return updateRecurringTemplate(districtId.value, editing.value.id, {
        ...changes, expected_revision: editing.value.revision,
      })
    }
    return createRecurringTemplate(districtId.value, input)
  })
  if (success) formOpen.value = false
}
function deactivateTemplate(item: RecurringTemplate): void {
  void perform(() => updateRecurringTemplate(districtId.value, item.id, {
    is_active: false, expected_revision: item.revision,
  }))
}

// Immediate watchers execute during setup: keep them after all reactive declarations.
watch(districtId, id => {
  fetchVersion++
  templates.value = []
  checklist.value = emptyPage()
  selected.value = new Set()
  pageOffset.value = 0
  loading.value = false
  preview.value = null
  formOpen.value = false
  if (id) {
    void districtsStore.fetchCongregations(id).catch(() => undefined)
    void load()
  }
}, { immediate: true })
</script>
