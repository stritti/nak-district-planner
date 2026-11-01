<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div class="p-4 sm:p-6 max-w-3xl">
    <h1 class="page-title">Erste Schritte</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
      Vom leeren Bezirk bis zum Kalender-Abo der Gemeinden. Jeder Schritt führt zur passenden Seite;
      der Stand gilt für
      <span class="font-medium text-gray-700 dark:text-gray-300">{{ districtsStore.selectedDistrict?.name ?? 'den gewählten Bezirk' }}</span>.
    </p>

    <div v-if="loading" class="text-sm text-gray-500 dark:text-gray-400">Lade…</div>
    <ErrorAlert v-else-if="error" :message="error" />

    <template v-else>
      <p
        v-if="allDone"
        class="card p-4 mb-4 text-sm text-green-800 dark:text-green-300 bg-green-50 dark:bg-green-900/20"
        data-testid="getting-started-done"
      >
        Alles eingerichtet. Neue Wochen plant die Matrix, freigegebene Gottesdienste erscheinen im Kalender-Abo.
      </p>

      <ol class="space-y-3" data-testid="getting-started-steps">
        <li
          v-for="(step, index) in steps"
          :key="step.id"
          class="card p-4 flex items-start gap-3"
          :class="step.id === nextId ? 'ring-2 ring-blue-500 dark:ring-blue-400' : ''"
          :data-testid="`step-${step.id}`"
          :data-state="step.state"
          :aria-current="step.id === nextId ? 'step' : undefined"
        >
          <CheckCircleIcon
            v-if="step.state === 'done'"
            class="h-6 w-6 shrink-0 text-green-600 dark:text-green-400"
            aria-hidden="true"
          />
          <QuestionMarkCircleIcon
            v-else-if="step.state === 'unknown'"
            class="h-6 w-6 shrink-0 text-gray-400 dark:text-gray-500"
            aria-hidden="true"
          />
          <span
            v-else
            class="h-6 w-6 shrink-0 rounded-full border-2 border-gray-300 dark:border-gray-600 text-xs font-medium text-gray-500 dark:text-gray-400 flex items-center justify-center"
            aria-hidden="true"
          >{{ index + 1 }}</span>

          <div class="min-w-0 flex-1">
            <h2 class="text-sm font-medium text-gray-900 dark:text-gray-100">
              {{ step.title }}
              <span class="sr-only">({{ STATE_LABEL[step.state] }})</span>
            </h2>
            <p class="text-sm text-gray-500 dark:text-gray-400">{{ step.detail }}</p>
            <p v-if="step.hint && step.state !== 'done'" class="text-xs text-gray-400 dark:text-gray-500 mt-1">
              {{ step.hint }}
            </p>
          </div>

          <RouterLink
            v-if="step.actionLabel"
            :to="step.to"
            class="shrink-0 text-sm whitespace-nowrap"
            :class="step.id === nextId ? 'btn-primary px-3 py-1.5' : 'text-blue-600 dark:text-blue-400 hover:underline py-1.5'"
          >
            {{ step.actionLabel }}
          </RouterLink>
        </li>
      </ol>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from 'vue'
import { routerKey } from 'vue-router'
import { CheckCircleIcon, QuestionMarkCircleIcon } from '@heroicons/vue/24/outline'
import ErrorAlert from '../components/ErrorAlert.vue'
import { listCongregations } from '../api/districts'
import { listLeaders } from '../api/leaders'
import { fetchMatrix } from '../api/matrix'
import { listExportTokens } from '../api/exportTokens'
import { userMessage } from '../api/errors'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import {
  GETTING_STARTED_WEEKS,
  gettingStartedSteps,
  nextStepId,
  type GettingStartedFacts,
} from '../utils/gettingStarted'

const STATE_LABEL = { done: 'erledigt', open: 'offen', unknown: 'unbekannt' } as const

const auth = useAuthStore()
const districtsStore = useDistrictsStore()
const router = inject(routerKey, null)

const loading = ref(true)
const error = ref<string | null>(null)
const facts = ref<GettingStartedFacts>({
  districtCount: 0, congregations: null, leaderCount: null, matrix: null, exportTokenCount: null,
})

const districtId = computed(() => districtsStore.selectedDistrictId)
const steps = computed(() => gettingStartedSteps(facts.value, {
  createDistrict: auth.isSuperadmin,
  adminDistrict: auth.canAdminDistrict(districtId.value),
  planDistrict: auth.canPlanDistrict(districtId.value),
}))
const nextId = computed(() => nextStepId(steps.value))
const allDone = computed(() => steps.value.every((step) => step.state === 'done'))

function value<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === 'fulfilled' ? result.value : null
}

/** Each fact loads on its own: a failing or forbidden request marks only its step unknown. */
let loadRun = 0

async function load(): Promise<void> {
  const run = ++loadRun
  loading.value = true
  error.value = null
  try {
    if (districtsStore.districts.length === 0) await districtsStore.fetchDistricts()
    const id = districtId.value
    if (!id) {
      facts.value = { ...facts.value, districtCount: districtsStore.districts.length }
      return
    }
    // The matrix filters by the UTC dates of both bounds (end inclusive), so send today's
    // calendar date at UTC midnight and the last day of the window.
    const today = new Date()
    const from = new Date(Date.UTC(today.getFullYear(), today.getMonth(), today.getDate()))
    const to = new Date(from)
    to.setUTCDate(to.getUTCDate() + 7 * GETTING_STARTED_WEEKS - 1)
    const [congregations, leaders, matrix, tokens] = await Promise.allSettled([
      listCongregations(id),
      listLeaders(id),
      fetchMatrix(id, from.toISOString(), to.toISOString()),
      auth.canAdminDistrict(id) ? listExportTokens(id) : Promise.reject(new Error('forbidden')),
    ])
    // A newer load (another district was selected meanwhile) owns the result.
    if (run !== loadRun) return
    facts.value = {
      districtCount: districtsStore.districts.length,
      congregations: value(congregations),
      leaderCount: value(leaders)?.length ?? null,
      matrix: value(matrix),
      exportTokenCount: value(tokens)?.filter((token) => token.district_id === id).length ?? null,
    }
  } catch (e) {
    if (run === loadRun) error.value = userMessage(e, 'Bezirke konnten nicht geladen werden.')
  } finally {
    if (run === loadRun) loading.value = false
  }
}

onMounted(() => {
  // The checklist guides planning; everyone else starts at the event list as before.
  if (!auth.canPlanAnyDistrict) {
    void router?.replace({ name: 'events' })
    return
  }
  void load()
})

watch(districtId, (next, previous) => {
  if (next && next !== previous) void load()
})
</script>
