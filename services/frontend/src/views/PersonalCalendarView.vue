<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  createPersonalToken,
  listPersonalEvents,
  listPersonalTokens,
  revokePersonalToken,
  type PersonalEvent,
  type PersonalToken,
} from '../api/personalCalendar'
import CopyButton from '../components/CopyButton.vue'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import { userMessage } from '../api/errors'

const auth = useAuthStore()
const districts = useDistrictsStore()
const from = ref(new Date().toISOString().slice(0, 10))
const to = ref(new Date(Date.now() + 90 * 86_400_000).toISOString().slice(0, 10))
const events = ref<PersonalEvent[]>([])
const tokens = ref<PersonalToken[]>([])
const eventsLoading = ref(false)
const tokensLoading = ref(false)
const savingFeed = ref(false)
const eventError = ref('')
const tokenError = ref('')
const actionError = ref('')
const loading = computed(() => eventsLoading.value || tokensLoading.value || savingFeed.value)
const error = computed(() => actionError.value || tokenError.value || eventError.value)
let eventVersion = 0
let tokenVersion = 0

watch(
  [() => districts.selectedDistrictId, () => auth.user?.sub, from, to],
  async ([district, subject]) => {
    const current = ++eventVersion
    events.value = []
    eventError.value = ''
    eventsLoading.value = false
    if (!district || !subject) return
    eventsLoading.value = true
    try {
      const entries = await listPersonalEvents(district, from.value, to.value)
      if (current === eventVersion) events.value = entries
    } catch (cause) {
      if (current === eventVersion) {
        eventError.value = cause instanceof Error
          ? cause.message
          : 'Kalender konnte nicht geladen werden'
      }
    } finally {
      if (current === eventVersion) eventsLoading.value = false
    }
  },
  { immediate: true },
)

// Secrets belong to an identity and district, independently of the event date filter.
watch(
  [() => districts.selectedDistrictId, () => auth.user?.sub],
  async ([district, subject]) => {
    const current = ++tokenVersion
    tokens.value = []
    tokenError.value = ''
    actionError.value = ''
    tokensLoading.value = false
    savingFeed.value = false
    if (!district || !subject) return
    tokensLoading.value = true
    try {
      const feeds = await listPersonalTokens(district, subject)
      if (current === tokenVersion) tokens.value = feeds
    } catch (cause) {
      if (current === tokenVersion) {
        tokenError.value = cause instanceof Error
          ? cause.message
          : 'Kalender konnte nicht geladen werden'
      }
    } finally {
      if (current === tokenVersion) tokensLoading.value = false
    }
  },
  { immediate: true },
)

function icsUrl(secret: string): string {
  return `${window.location.origin}/api/v1/export/${encodeURIComponent(secret)}/calendar.ics`
}

async function createFeed() {
  const district = districts.selectedDistrictId
  const subject = auth.user?.sub
  const current = tokenVersion
  if (!district || !subject || loading.value) return
  savingFeed.value = true
  actionError.value = ''
  try {
    const token = await createPersonalToken(district, subject)
    if (current === tokenVersion) tokens.value.push(token)
  } catch (cause) {
    if (current === tokenVersion) {
      actionError.value = cause instanceof Error
        ? cause.message
        : 'Kalenderlink konnte nicht erstellt werden'
    }
  } finally {
    if (current === tokenVersion) savingFeed.value = false
  }
}

async function revoke(id: string) {
  if (loading.value) return
  const current = tokenVersion
  savingFeed.value = true
  actionError.value = ''
  try {
    await revokePersonalToken(id)
    if (current === tokenVersion) {
      tokens.value = tokens.value.filter(token => token.id !== id)
    }
  } catch (cause) {
    if (current === tokenVersion) {
      actionError.value = userMessage(cause, 'Widerruf fehlgeschlagen')
    }
  } finally {
    if (current === tokenVersion) savingFeed.value = false
  }
}
</script>

<template>
  <main class="max-w-4xl space-y-4 p-6">
    <h1 class="text-xl font-semibold">Mein Kalender</h1>
    <p class="text-sm text-gray-600">
      Persönliche Termine enthalten nur Dienste, die Ihrem verknüpften Konto
      zugeordnet sind. Kalenderlinks sind privat.
    </p>
    <p v-if="!districts.selectedDistrictId">Bitte einen Bezirk auswählen.</p>
    <div class="flex gap-4">
      <label>
        Von
        <input v-model="from" type="date" class="form-input" />
      </label>
      <label>
        Bis
        <input v-model="to" type="date" class="form-input" :min="from" />
      </label>
    </div>
    <p v-if="loading" role="status">Laden…</p>
    <p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
    <p v-if="!loading && !error && !events.length">Keine persönlichen Termine im Zeitraum.</p>

    <article
      v-for="event in events"
      :key="event.uid"
      data-testid="personal-event"
      class="space-y-1 rounded border p-3"
    >
      <h2 class="font-semibold">{{ event.title }}</h2>
      <p>
        {{ new Date(event.start_at).toLocaleString('de-DE') }} –
        {{ new Date(event.end_at).toLocaleTimeString('de-DE') }}
      </p>
      <p>{{ event.duties.join(', ') }}</p>
      <p v-if="event.status === 'CANCELLED'" class="text-red-600">Abgesagt</p>
    </article>

    <h2 class="font-semibold">Private Kalenderabonnements</h2>
    <button
      data-testid="create-feed"
      class="btn-primary"
      :disabled="loading || !districts.selectedDistrictId || !auth.user?.sub"
      @click="createFeed"
    >
      Kalenderlink erstellen
    </button>
    <div
      v-for="token in tokens"
      :key="token.id"
      class="flex flex-wrap items-center gap-3"
    >
      <a
        v-if="token.token"
        :href="icsUrl(token.token)"
        class="text-blue-600 underline"
      >
        {{ token.label }} (ICS)
      </a>
      <span v-if="token.token" class="text-xs text-amber-700 dark:text-amber-300">
        Secret nur jetzt sichtbar — bitte kopieren
      </span>
      <CopyButton
        v-if="token.token"
        :value="icsUrl(token.token)"
        label="URL kopieren"
        variant="icon"
      />
      <span v-else class="text-sm text-gray-500 dark:text-gray-400">
        {{ token.label }} — Secret nur direkt nach dem Erstellen sichtbar
      </span>
      <button class="btn-secondary" :disabled="loading" @click="revoke(token.id)">
        Widerrufen
      </button>
    </div>
  </main>
</template>
