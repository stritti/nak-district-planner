<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div class="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-4">
    <div class="w-full max-w-lg">
      <ContextualHelp context="registration" />
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

          <!-- The account is created by the user in Keycloak; the approval is linked at the
               first login through the verified email address. -->
          <p v-if="accountLinked" class="mt-4 text-sm text-gray-600" data-testid="account-linked">
            Die Registrierung ist mit Ihrem angemeldeten Konto verknüpft.
          </p>
          <div v-else class="mt-6 border-t border-gray-200 pt-6" data-testid="create-account">
            <p class="text-sm text-gray-600 mb-4">
              Legen Sie jetzt Ihr Konto an. Verwenden Sie dabei dieselbe E-Mail-Adresse
              (<strong>{{ submittedEmail }}</strong>) und bestätigen Sie sie über den Link in der
              E-Mail. Nach der Freischaltung erhalten Sie beim nächsten Anmelden Zugriff.
            </p>
            <p v-if="accountError" class="mb-3 text-sm text-red-600" role="alert">{{ accountError }}</p>
            <button
              type="button"
              class="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium transition-colors"
              :disabled="creatingAccount"
              @click="createAccount"
            >
              {{ creatingAccount ? 'Weiterleitung…' : 'Konto anlegen' }}
            </button>
            <p class="mt-3 text-xs text-gray-500">
              Sie haben bereits ein Konto?
              <RouterLink to="/login" class="text-blue-500 hover:underline">Anmelden</RouterLink>
            </p>
          </div>
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
              :readonly="!!accountEmail"
              :class="{ 'bg-gray-100 text-gray-600': accountEmail }"
            />
            <p v-if="accountEmail" data-testid="account-email-hint" class="mt-1 text-xs text-gray-500">
              Die Registrierung wird mit Ihrem angemeldeten Konto verknüpft und verwendet dessen E-Mail-Adresse.
            </p>
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
              <option v-for="r in roleChoicesFor(form.congregation_id)" :key="r.value" :value="r.value">{{ r.label }}</option>
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
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { CheckCircleIcon } from '@heroicons/vue/24/outline'
import ContextualHelp from '../components/ContextualHelp.vue'
import { useOIDC } from '../composables/useOIDC'
import { useAuthStore } from '../stores/auth'
import { LEADER_RANKS } from '../api/leaders'
import { roleChoicesFor, roleFitsLevel } from '../api/leaderRoles'
import type { LeaderRank, SpecialRole } from '../api/leaders'
import {
  listDistrictsPublic,
  listCongregationsPublic,
  submitRegistration,
  type PublicDistrictInfo,
  type PublicCongregationInfo,
} from '../api/registrations'
import { userMessage } from '../api/errors'

const oidc = useOIDC(useRouter())
const authStore = useAuthStore()

const submitted = ref(false)
const submitting = ref(false)
const error = ref<string | null>(null)
// Email of the submitted registration (shown in the account hint) and whether the request
// carried the token of a logged-in user, which binds the registration to that account.
const submittedEmail = ref('')
const accountLinked = ref(false)
const creatingAccount = ref(false)
const accountError = ref<string | null>(null)

// A logged-in user's registration is bound to the account's verified email; the server
// rejects any other address, so the field mirrors the account and is not editable.
const accountEmail = computed(() =>
  authStore.isAuthenticated ? authStore.user?.email?.trim() || null : null,
)

const districts = ref<PublicDistrictInfo[]>([])
const congregations = ref<PublicCongregationInfo[]>([])

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

watch(
  accountEmail,
  (email) => {
    if (email) form.value.email = email
  },
  { immediate: true },
)

listDistrictsPublic()
  .then((d) => (districts.value = d))
  .catch(() => {
    error.value = 'Bezirke konnten nicht geladen werden. Bitte Seite neu laden.'
  })

// A role that no longer fits the chosen congregation would be rejected by the server.
watch(
  () => [form.value.congregation_id, form.value.special_role] as const,
  ([congregationId, role]) => {
    if (role && !roleFitsLevel(role, congregationId)) form.value.special_role = null
  },
)

watch(
  () => form.value.district_id,
  async (districtId, _previousDistrictId, onCleanup) => {
    // Vue invalidates the previous watcher before running the next one.
    // A slower request must never restore options from a former district.
    let isCurrent = true
    onCleanup(() => { isCurrent = false })

    form.value.congregation_id = null
    congregations.value = []
    if (!districtId) return

    try {
      const options = await listCongregationsPublic(districtId)
      if (isCurrent) congregations.value = options
    } catch {
      if (isCurrent) congregations.value = []
    }
  },
)

async function handleSubmit() {
  if (!form.value.district_id) return
  error.value = null
  submitting.value = true
  try {
    const accessToken = authStore.getToken()
    await submitRegistration(
      form.value.district_id,
      {
        name: form.value.name,
        email: form.value.email,
        rank: form.value.rank || null,
        congregation_id: form.value.congregation_id || null,
        special_role: form.value.special_role || null,
        phone: form.value.phone || null,
        notes: form.value.notes || null,
      },
      accessToken,
    )
    submittedEmail.value = form.value.email
    accountLinked.value = !!accessToken
    submitted.value = true
  } catch (err) {
    error.value = userMessage(err, 'Fehler beim Einreichen der Registrierung.')
  } finally {
    submitting.value = false
  }
}

/** Open the realm's registration form (OIDC prompt=create) to create the Keycloak account. */
async function createAccount() {
  accountError.value = null
  creatingAccount.value = true
  try {
    window.location.href = await oidc.getAuthorizationUrl({ prompt: 'create' })
  } catch (err) {
    accountError.value = userMessage(err, 'Weiterleitung fehlgeschlagen')
    creatingAccount.value = false
  }
}
</script>
