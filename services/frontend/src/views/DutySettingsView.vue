<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  createDutyCategory,
  listDutyCategories,
  putDutyConfiguration,
  restoreDutyInheritance,
  updateDutyCategory,
  type DutyCategory,
} from '../api/eventDuties'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import { userMessage } from '../api/errors'

const districts = useDistrictsStore()
const auth = useAuthStore()
const scope = ref('')
const loading = ref(false)
const error = ref('')

type Row = DutyCategory & {
  override: boolean
  inherited: boolean
  eventText: string
}

const rows = ref<Row[]>([])
const label = ref('')
const code = ref('')
const canManage = computed(() =>
  auth.isSuperadmin || auth.memberships.some(membership =>
    (
      membership.scope_type === 'DISTRICT'
      && membership.scope_id === districts.selectedDistrictId
      && membership.role === 'DISTRICT_ADMIN'
    ) || (
      Boolean(scope.value)
      && membership.scope_type === 'CONGREGATION'
      && membership.scope_id === scope.value
      && membership.role === 'CONGREGATION_ADMIN'
    ),
  ),
)
let version = 0

async function load() {
  const current = ++version
  rows.value = []
  error.value = ''
  if (!districts.selectedDistrictId) return
  loading.value = true
  try {
    const data = await listDutyCategories(
      districts.selectedDistrictId,
      scope.value || undefined,
    )
    if (current === version) {
      rows.value = data.categories.map(category => {
        const override = data.overrides.find(
          item => item.duty_category_id === category.id,
        )
        return {
          ...category,
          ...(override
            ? {
                enabled: override.enabled,
                capacity: override.capacity,
                event_categories: override.event_categories,
              }
            : {}),
          override: Boolean(override),
          inherited: Boolean(scope.value) && !category.congregation_id,
          eventText: (override?.event_categories ?? category.event_categories).join(', '),
        }
      })
    }
  } catch (cause) {
    if (current === version) {
      error.value = cause instanceof Error
        ? cause.message
        : 'Konfiguration konnte nicht geladen werden'
    }
  } finally {
    if (current === version) loading.value = false
  }
}

async function loadDistrict(districtId: string) {
  try {
    scope.value = ''
    if (districtId) await districts.fetchCongregations(districtId)
    if (districts.selectedDistrictId === districtId) await load()
  } catch (cause) {
    if (districts.selectedDistrictId === districtId) {
      error.value = cause instanceof Error
        ? cause.message
        : 'Gemeinden konnten nicht geladen werden'
    }
  }
}

watch(
  () => districts.selectedDistrictId,
  districtId => { void loadDistrict(districtId) },
  { immediate: true },
)
watch(scope, () => { void load() })

async function save(row: Row) {
  if (!canManage.value || loading.value) return
  loading.value = true
  error.value = ''
  const data = {
    enabled: row.enabled,
    capacity: Number(row.capacity),
    event_categories: row.eventText
      .split(',')
      .map(item => item.trim())
      .filter(Boolean),
  }
  try {
    if (row.inherited) {
      await putDutyConfiguration(districts.selectedDistrictId, {
        ...data,
        congregation_id: scope.value,
        duty_category_id: row.id,
      })
    } else {
      await updateDutyCategory(districts.selectedDistrictId, row.id, data)
    }
    await load()
  } catch (cause) {
    error.value = userMessage(cause, 'Speichern fehlgeschlagen')
  } finally {
    loading.value = false
  }
}

async function restore(row: Row) {
  if (!canManage.value || loading.value) return
  loading.value = true
  error.value = ''
  try {
    await restoreDutyInheritance(districts.selectedDistrictId, row.id, scope.value)
    await load()
  } catch (cause) {
    error.value = cause instanceof Error
      ? cause.message
      : 'Wiederherstellen fehlgeschlagen'
  } finally {
    loading.value = false
  }
}

async function create() {
  if (
    !canManage.value
    || loading.value
    || !label.value.trim()
    || !code.value.trim()
  ) return
  loading.value = true
  error.value = ''
  try {
    await createDutyCategory(districts.selectedDistrictId, {
      congregation_id: scope.value || null,
      code: code.value.trim(),
      label: label.value.trim(),
      event_categories: [],
      enabled: true,
      capacity: 1,
    })
    label.value = ''
    code.value = ''
    await load()
  } catch (cause) {
    error.value = userMessage(cause, 'Anlegen fehlgeschlagen')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="max-w-4xl space-y-4 p-6">
    <h1 class="text-xl font-semibold">Organisatorische Dienste konfigurieren</h1>
    <p class="text-sm text-gray-600">
      Alle Zuordnungen sind freiwillig. Änderungen erhalten bestehende Zuordnungen;
      überschrittene Kapazitäten werden zur Prüfung markiert.
    </p>
    <label class="block">
      Geltungsbereich
      <select v-model="scope" data-testid="scope" class="form-input">
        <option value="">Bezirk</option>
        <option
          v-for="congregation in districts.congregations"
          :key="congregation.id"
          :value="congregation.id"
        >
          {{ congregation.name }}
        </option>
      </select>
    </label>
    <p v-if="!districts.selectedDistrictId">Bitte einen Bezirk auswählen.</p>
    <p v-if="loading" role="status">Laden…</p>
    <p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
    <p v-if="!canManage">Keine Verwaltungsberechtigung für diesen Bereich.</p>

    <section v-for="row in rows" :key="row.id" class="space-y-3 rounded border p-4">
      <h2 class="font-semibold">{{ row.label }}</h2>
      <p class="text-sm text-gray-500">
        {{ row.override ? 'Lokale Abweichung' : row.inherited ? 'Vom Bezirk geerbt' : 'Eigene Definition' }}
      </p>
      <label class="flex gap-2">
        <input v-model="row.enabled" type="checkbox" :disabled="!canManage || loading" />
        Aktiviert
      </label>
      <label class="block">
        Kapazität
        <input
          v-model.number="row.capacity"
          data-testid="capacity"
          type="number"
          min="1"
          class="form-input"
          :disabled="!canManage || loading"
        />
      </label>
      <label class="block">
        Exakte Ereigniskategorien (kommagetrennt; leer = alle)
        <input v-model="row.eventText" class="form-input" :disabled="!canManage || loading" />
      </label>
      <div v-if="canManage" class="flex gap-3">
        <button
          data-testid="save-config"
          class="btn-primary"
          :disabled="loading || row.capacity < 1"
          @click="save(row)"
        >
          Speichern
        </button>
        <button
          v-if="row.override"
          data-testid="restore-config"
          class="btn-secondary"
          :disabled="loading"
          @click="restore(row)"
        >
          Vererbung wiederherstellen
        </button>
      </div>
    </section>

    <form
      v-if="canManage && districts.selectedDistrictId"
      class="space-y-2 rounded border p-4"
      @submit.prevent="create"
    >
      <h2 class="font-semibold">Neuen Dienst anlegen</h2>
      <label class="block">
        Bezeichnung
        <input v-model="label" class="form-input" maxlength="200" required />
      </label>
      <label class="block">
        Eindeutiger Code
        <input v-model="code" class="form-input" maxlength="80" required />
      </label>
      <button class="btn-primary" :disabled="loading">Anlegen</button>
    </form>
  </main>
</template>
