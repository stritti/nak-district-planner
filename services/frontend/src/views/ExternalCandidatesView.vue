<template>
  <main class="max-w-5xl mx-auto p-4 sm:p-6">
    <div class="flex items-center justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-100">Externe Termine prüfen</h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Noch nicht zugeordnete Termine werden erst nach deiner Entscheidung in die Planung übernommen.
        </p>
      </div>
    </div>

    <div v-if="!districtId" class="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
      Bitte zuerst einen Bezirk auswählen.
    </div>
    <div v-else-if="store.loading" class="py-12 text-center text-sm text-gray-500">Kandidaten werden geladen…</div>
    <div v-else-if="store.loadError" class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      {{ store.loadError }}
    </div>
    <template v-else>
      <div
        v-if="store.reviewError"
        class="rounded-lg border border-red-200 bg-red-50 p-4 mb-4 text-sm text-red-700"
        role="alert"
      >
        {{ store.reviewError }}
      </div>

      <div v-if="store.items.length === 0" class="rounded-lg border border-gray-200 dark:border-gray-700 p-8 text-center text-sm text-gray-500">
        Keine offenen externen Termine.
      </div>

      <div v-else class="space-y-4">
        <article
          v-for="candidate in store.items"
          :key="candidate.id"
          class="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-5"
        >
          <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div>
              <h2 class="font-semibold text-gray-900 dark:text-gray-100">{{ candidate.title }}</h2>
              <p class="text-sm text-gray-500 mt-1">{{ formatPeriod(candidate.start_at, candidate.end_at) }}</p>
              <p v-if="candidate.category" class="text-xs text-gray-500 mt-1">Kategorie: {{ candidate.category }}</p>
              <p v-if="candidate.description" class="text-sm text-gray-700 dark:text-gray-300 mt-3 whitespace-pre-line">
                {{ candidate.description }}
              </p>
            </div>
            <span class="text-xs rounded-full bg-amber-100 text-amber-800 px-2 py-1 self-start">Prüfung offen</span>
          </div>

          <div class="flex flex-wrap justify-end gap-2 mt-5">
            <button
              class="btn-secondary px-4 py-2"
              :disabled="store.reviewingId === candidate.id"
              @click="store.dismiss(candidate.id)"
            >
              Verwerfen
            </button>
            <button
              class="btn-primary px-4 py-2"
              :disabled="store.reviewingId === candidate.id"
              @click="store.acceptAndCreate(candidate.id)"
            >
              {{ store.reviewingId === candidate.id ? 'Speichern…' : 'Als neuen Termin übernehmen' }}
            </button>
          </div>
        </article>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useDistrictsStore } from '../stores/districts'
import { useExternalCandidatesStore } from '../stores/externalCandidates'

const districts = useDistrictsStore()
const store = useExternalCandidatesStore()
const districtId = computed(() => districts.selectedDistrictId)

watch(districtId, (id) => {
  if (id) void store.fetchPending(id)
}, { immediate: true })

function formatPeriod(start: string, end: string): string {
  const formatter = new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' })
  return `${formatter.format(new Date(start))} bis ${formatter.format(new Date(end))}`
}
</script>
