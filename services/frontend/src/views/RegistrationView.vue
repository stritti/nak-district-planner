<template>
  <div class="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-4">
    <div class="w-full max-w-lg">
      <div class="bg-white rounded-xl shadow-lg p-8">
        <!-- Header -->
        <div class="text-center mb-8">
          <h1 class="text-2xl font-bold text-gray-900 mb-1">NAK Bezirksplaner</h1>
          <p class="text-gray-500 text-sm">Registrierung als Amtstragender</p>
        </div>

        <!-- Success State -->
        <div v-if="submitted" class="text-center py-6">
          <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <CheckCircleIcon class="h-10 w-10 text-green-600" />
          </div>
          <h2 class="text-xl font-semibold text-gray-900 mb-2">Registrierung eingereicht</h2>
          <p class="text-gray-500 text-sm">
            Ihre Registrierungsanfrage wurde übermittelt. Der Bezirksadministrator wird sie prüfen
            und Sie gegebenenfalls freischalten.
          </p>
        </div>

        <!-- Form -->
        <form v-else @submit.prevent="handleSubmit" class="space-y-5">
          <!-- District selection -->
          <div>
            <label class="form-label">Bezirk <span class="text-red-500">*</span></label>
            <select
              v-model="form.district_id"
              class="form-select w-full"
              required
            >
              <option value="">Bezirk wählen…</option>
              <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
            </select>
          </div>

          <!-- Name -->
          <div>
            <label class="form-label">Name <span class="text-red-500">*</span></label>
            <input
              v-model="form.name"
              type="text"
              class="form-input w-full"
              placeholder="Vor- und Nachname"
              required
              maxlength="255"
            />
          </div>

          <!-- Email -->
          <div>
            <label class="form-label">E-Mail <span class="text-red-500">*</span></label>
            <input
              v-model="form.email"
              type="email"
              class="form-input w-full"
              placeholder="name@beispiel.de"
              required
            />
          </div>

          <!-- Rank -->
          <div>
            <label class="form-label">Grad</label>
            <select v-model="form.rank" class="form-select w-full">
              <option :value="null">— kein Grad angegeben —</option>
              <option v-for="r in LEADER_RANKS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>

          <!-- Congregation (optional, loaded when district is selected) -->
          <div v-if="form.district_id">
            <label class="form-label">Heimat-Gemeinde</label>
            <select v-model="form.congregation_id" class="form-select w-full">
              <option :value="null">— Gemeinde nicht bekannt —</option>
              <option v-for="c in congregations" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>

          <!-- Special role -->
          <div>
            <label class="form-label">Beauftragung</label>
            <select v-model="form.special_role" class="form-select w-full">
              <option :value="null">— keine —</option>
              <option v-for="r in SPECIAL_ROLES" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>

          <!-- Phone -->
          <div>
            <label class="form-label">Telefon</label>
            <input
              v-model="form.phone"
              type="tel"
              class="form-input w-full"
              placeholder="+49 …"
              maxlength="100"
            />
          </div>

          <!-- Notes -->
          <div>
            <label class="form-label">Anmerkungen</label>
            <textarea
              v-model="form.notes"
              rows="3"
              class="form-input w-full resize-none"
              placeholder="Optionale Nachricht an den Administrator"
            />
          </div>

          <!-- Error -->
          <div v-if="error" class="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {{ error }}
          </div>

          <!-- Submit -->
          <button
            type="submit"
            :disabled="submitting || !form.district_id"
            class="w-full py-2.5 rounded-lg font-medium text-white transition-colors"
            :class="submitting || !form.district_id
              ? 'bg-blue-300 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'"
          >
            <span v-if="submitting" class="flex items-center justify-center gap-2">
              <span class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Wird übermittelt…
            </span>
            <span v-else>Registrierung einreichen</span>
          </button>

          <p class="text-center text-xs text-gray-400">
            Bereits registriert?
            <RouterLink to="/login" class="text-blue-500 hover:underline">Anmelden</RouterLink>
          </p>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { CheckCircleIcon } from '@heroicons/vue/24/outline'
import { LEADER_RANKS, SPECIAL_ROLES } from '@/api/leaders'
import type { LeaderRank, SpecialRole } from '@/api/leaders'
import { listDistricts, listCongregations } from '@/api/districts'
import type { DistrictResponse, CongregationResponse } from '@/api/districts'

// For public calls we skip the auth wrapper and use raw fetch
async function publicPost<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}${text ? ': ' + text : ''}`)
  }
  return res.json() as Promise<T>
}

const submitted = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)

const districts = ref<DistrictResponse[]>([])
const congregations = ref<CongregationResponse[]>([])

const form = ref<{
  district_id: string
  name: string
  email: string
  rank: LeaderRank | null
  congregation_id: string | null
  special_role: SpecialRole | null
  phone: string
  notes: string
}>({
  district_id: '',
  name: '',
  email: '',
  rank: null,
  congregation_id: null,
  special_role: null,
  phone: '',
  notes: '',
})

// Load districts on mount (public, no auth needed)
listDistricts()
  .then((d) => (districts.value = d))
  .catch(() => {
    error.value = 'Bezirke konnten nicht geladen werden. Bitte Seite neu laden.'
  })

// Load congregations when district changes
watch(
  () => form.value.district_id,
  async (id) => {
    form.value.congregation_id = null
    if (!id) {
      congregations.value = []
      return
    }
    try {
      congregations.value = await listCongregations(id)
    } catch {
      congregations.value = []
    }
  },
)

async function handleSubmit() {
  if (!form.value.district_id) return
  error.value = null
  submitting.value = true
  try {
    await publicPost(`/api/v1/districts/${form.value.district_id}/registrations`, {
      name: form.value.name,
      email: form.value.email,
      rank: form.value.rank || null,
      congregation_id: form.value.congregation_id || null,
      special_role: form.value.special_role || null,
      phone: form.value.phone || null,
      notes: form.value.notes || null,
    })
    submitted.value = true
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Fehler beim Einreichen der Registrierung.'
  } finally {
    submitting.value = false
  }
}
</script>
