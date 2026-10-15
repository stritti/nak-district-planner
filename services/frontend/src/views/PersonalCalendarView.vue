<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import { listPersonalEvents, listPersonalTokens, createPersonalToken, revokePersonalToken, type PersonalEvent, type PersonalToken } from '../api/personalCalendar'
const auth = useAuthStore(), districts = useDistrictsStore()
const from = ref(new Date().toISOString().slice(0,10)), to = ref(new Date(Date.now()+90*86400000).toISOString().slice(0,10))
const events = ref<PersonalEvent[]>([]), tokens = ref<PersonalToken[]>([]), loading = ref(false), error = ref('')
let version = 0
watch([() => districts.selectedDistrictId, () => auth.user?.sub, from, to], async ([district, subject]) => {
 const current = ++version; events.value = []; tokens.value = []; error.value = ''
 if (!district || !subject) return
 loading.value = true
 try {
  const [entries, feeds] = await Promise.all([listPersonalEvents(district, from.value, to.value), listPersonalTokens(district, subject)])
  if (current === version) { events.value = entries; tokens.value = feeds }
 } catch (cause) { if(current === version) error.value = cause instanceof Error ? cause.message : 'Kalender konnte nicht geladen werden' }
 finally { if(current === version) loading.value = false }
}, { immediate: true })
async function createFeed() {
 const district = districts.selectedDistrictId, subject = auth.user?.sub, current = version
 if (!district || !subject || loading.value) return
 loading.value = true; error.value = ''
 try { const token = await createPersonalToken(district, subject); if(current === version) tokens.value.push(token) }
 catch(cause) { if(current === version) error.value = cause instanceof Error ? cause.message : 'Kalenderlink konnte nicht erstellt werden' }
 finally { if(current === version) loading.value = false }
}
async function revoke(id: string) {
 const current = version; loading.value = true; error.value = ''
 try { await revokePersonalToken(id); if(current === version) tokens.value = tokens.value.filter(t => t.id !== id) }
 catch(cause) { if(current === version) error.value = cause instanceof Error ? cause.message : 'Widerruf fehlgeschlagen' }
 finally { if(current === version) loading.value = false }
}
</script>
<template>
 <main class="max-w-4xl p-6 space-y-4">
  <h1 class="text-xl font-semibold">Mein Kalender</h1>
  <p class="text-sm text-gray-600">Persönliche Termine enthalten nur Dienste, die Ihrem verknüpften Konto zugeordnet sind. Kalenderlinks sind privat.</p>
  <p v-if="!districts.selectedDistrictId">Bitte einen Bezirk auswählen.</p>
  <div class="flex gap-4"><label>Von<input v-model="from" type="date" class="form-input" /></label><label>Bis<input v-model="to" type="date" class="form-input" :min="from" /></label></div>
  <p v-if="loading" role="status">Laden…</p><p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
  <p v-if="!loading && !error && !events.length">Keine persönlichen Termine im Zeitraum.</p>
  <article v-for="event in events" :key="event.uid" data-testid="personal-event" class="rounded border p-3 space-y-1">
   <h2 class="font-semibold">{{ event.title }}</h2><p>{{ new Date(event.start_at).toLocaleString('de-DE') }} – {{ new Date(event.end_at).toLocaleTimeString('de-DE') }}</p>
   <p>{{ event.duties.join(', ') }}</p><p v-if="event.status === 'CANCELLED'" class="text-red-600">Abgesagt</p>
  </article>
  <h2 class="font-semibold">Private Kalenderabonnements</h2>
  <button data-testid="create-feed" class="btn-primary" :disabled="loading || !districts.selectedDistrictId || !auth.user?.sub" @click="createFeed">Kalenderlink erstellen</button>
  <div v-for="token in tokens" :key="token.id" class="flex flex-wrap gap-3 items-center"><a :href="`/api/v1/export/${encodeURIComponent(token.token)}/calendar.ics`" class="text-blue-600 underline">{{ token.label }} (ICS)</a><button class="btn-secondary" :disabled="loading" @click="revoke(token.id)">Widerrufen</button></div>
 </main>
</template>
