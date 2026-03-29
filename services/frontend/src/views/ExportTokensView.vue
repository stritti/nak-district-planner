<template>
  <div class="p-6 max-w-3xl">
    <div class="flex items-center justify-between mb-5">
      <h1 class="page-title mb-0">Kalender-Export</h1>
      <button
        class="btn-primary"
        @click="openCreate"
      >
        <PlusIcon class="h-4 w-4" />
        Neuer Token
      </button>
    </div>

    <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
      Erstelle ICS-Export-Links für Bezirke oder einzelne Gemeinden. Öffentliche Tokens
      anonymisieren den Dienstleiter-Namen; interne Tokens zeigen den vollen Namen.
    </p>

    <div v-if="loading" class="text-sm text-gray-500 dark:text-gray-400">Lade…</div>
    <div v-else-if="error" class="text-sm text-red-600 dark:text-red-400">{{ error }}</div>

    <!-- Token list -->
    <div v-else class="space-y-3">
      <div
        v-for="t in tokens"
        :key="t.id"
        class="card p-4"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="font-medium text-gray-900 dark:text-gray-100 truncate">{{ t.label }}</span>
              <span
                class="badge"
                :class="t.token_type === 'INTERNAL' ? 'bg-yellow-100 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-300' : 'bg-green-100 dark:bg-green-900/20 text-green-800 dark:text-green-300'"
              >
                {{ t.token_type === 'INTERNAL' ? 'Intern' : 'Öffentlich' }}
              </span>
            </div>
            <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
              {{ districtName(t.district_id) }}
              <template v-if="t.congregation_id">
                › {{ congregationName(t.congregation_id) }}
              </template>
            </div>
            <!-- ICS URL -->
            <div class="flex items-center gap-2">
              <code class="text-xs bg-gray-100 dark:bg-gray-700 rounded px-2 py-1 text-gray-700 dark:text-gray-300 truncate max-w-sm block">
                {{ icsUrl(t.token) }}
              </code>
              <button
                class="btn-icon shrink-0"
                title="URL kopieren"
                @click="copyUrl(t.token)"
              >
                <ClipboardDocumentIcon class="h-4 w-4" />
              </button>
              <a
                :href="icsUrl(t.token)"
                target="_blank"
                class="btn-icon shrink-0"
                title="Im Browser öffnen"
              >
                <ArrowTopRightOnSquareIcon class="h-4 w-4" />
              </a>
            </div>
            <p v-if="copiedToken === t.token" class="text-xs text-green-600 mt-1">Kopiert!</p>
          </div>
          <button
            class="btn-icon hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 shrink-0"
            title="Token löschen"
            @click="confirmDelete(t)"
          >
            <TrashIcon class="h-4 w-4" />
          </button>
        </div>
      </div>

      <div v-if="!loading && tokens.length === 0" class="text-sm text-gray-500 dark:text-gray-400">
        Noch keine Export-Tokens angelegt.
      </div>
    </div>

    <!-- Create modal -->
    <div
      v-if="form.open"
      class="modal-backdrop"
      @click.self="form.open = false"
    >
      <div class="modal-panel max-w-md">
        <div class="flex items-center justify-between mb-4">
          <h2 class="modal-title">Neuer Export-Token</h2>
          <button class="modal-close" @click="form.open = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <div class="space-y-4">
          <div>
            <label class="form-label">Bezeichnung</label>
            <input
              v-model="form.label"
              type="text"
              placeholder="z. B. Bezirk Nord – Öffentlich"
              class="form-input"
            />
          </div>

          <div>
            <label class="form-label">Typ</label>
            <select
              v-model="form.token_type"
              class="form-input"
            >
              <option value="PUBLIC">Öffentlich (Dienstleiter anonymisiert)</option>
              <option value="INTERNAL">Intern (Dienstleiter sichtbar)</option>
            </select>
          </div>

          <div>
            <label class="form-label">Bezirk</label>
            <select
              v-model="form.district_id"
              class="form-input"
              @change="onFormDistrictChange"
            >
              <option value="">Bezirk wählen…</option>
              <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">
                {{ d.name }}
              </option>
            </select>
          </div>

          <div>
            <label class="form-label">
              Gemeinde <span class="text-gray-400 dark:text-gray-500 font-normal">(optional — leer = ganzer Bezirk)</span>
            </label>
            <select
              v-model="form.congregation_id"
              :disabled="!form.district_id || formCongregations.length === 0"
              class="form-input disabled:bg-gray-50 dark:disabled:bg-gray-700 disabled:text-gray-400"
            >
              <option value="">Ganzer Bezirk</option>
              <option v-for="c in formCongregations" :key="c.id" :value="c.id">
                {{ c.name }}
              </option>
            </select>
          </div>
        </div>

        <p v-if="form.error" class="text-sm text-red-600 dark:text-red-400 mt-3">{{ form.error }}</p>

        <div class="flex justify-end gap-3 mt-5">
          <button
            class="text-sm px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
            @click="form.open = false"
          >
            Abbrechen
          </button>
          <button
            class="flex items-center gap-1.5 text-sm px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            :disabled="!form.label.trim() || !form.district_id || form.saving"
            @click="saveToken"
          >
            <LinkIcon class="h-4 w-4" />
            {{ form.saving ? 'Erstellen…' : 'Token erstellen' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Delete confirm modal -->
    <div
      v-if="deleteTarget"
      class="modal-backdrop"
      @click.self="deleteTarget = null"
    >
      <div class="modal-panel max-w-sm">
        <h2 class="modal-title mb-2">Token löschen?</h2>
        <p class="text-sm text-gray-600 dark:text-gray-400 mb-5">
          Der Token <strong>{{ deleteTarget.label }}</strong> wird unwiderruflich gelöscht.
          Bestehende Kalender-Abonnements funktionieren danach nicht mehr.
        </p>
        <div class="flex justify-end gap-3">
          <button
            class="btn-secondary"
            @click="deleteTarget = null"
          >
            Abbrechen
          </button>
          <button
            class="btn-primary px-4 py-2 bg-red-600 hover:bg-red-700"
            :disabled="deleting"
            @click="doDelete"
          >
            {{ deleting ? 'Löschen…' : 'Löschen' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  ArrowTopRightOnSquareIcon,
  ClipboardDocumentIcon,
  LinkIcon,
  PlusIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import {
  createExportToken,
  deleteExportToken,
  listExportTokens,
  type ExportTokenResponse,
} from '@/api/exportTokens'
import { listCongregations, type CongregationResponse } from '@/api/districts'
import { useDistrictsStore } from '@/stores/districts'

const districtsStore = useDistrictsStore()
const tokens = ref<ExportTokenResponse[]>([])
const loading = ref(false)
const error = ref('')
const copiedToken = ref<string | null>(null)
const deleteTarget = ref<ExportTokenResponse | null>(null)
const deleting = ref(false)
const formCongregations = ref<CongregationResponse[]>([])

const form = reactive({
  open: false,
  label: '',
  token_type: 'PUBLIC' as 'PUBLIC' | 'INTERNAL',
  district_id: '',
  congregation_id: '',
  saving: false,
  error: '',
})

onMounted(async () => {
  loading.value = true
  try {
    if (districtsStore.districts.length === 0) await districtsStore.fetchDistricts()
    tokens.value = await listExportTokens()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Fehler beim Laden'
  } finally {
    loading.value = false
  }
})

// ── Helpers ──────────────────────────────────────────────────────────────────

const allCongregations = ref<CongregationResponse[]>([])

async function ensureAllCongregations() {
  if (allCongregations.value.length > 0) return
  const lists = await Promise.all(
    districtsStore.districts.map((d) => listCongregations(d.id)),
  )
  allCongregations.value = lists.flat()
}

function districtName(id: string): string {
  return districtsStore.districts.find((d) => d.id === id)?.name ?? id
}

function congregationName(id: string): string {
  return allCongregations.value.find((c) => c.id === id)?.name ?? id
}

function icsUrl(token: string): string {
  return `${window.location.origin}/api/v1/export/${token}/calendar.ics`
}

async function copyUrl(token: string) {
  await navigator.clipboard.writeText(icsUrl(token))
  copiedToken.value = token
  setTimeout(() => { copiedToken.value = null }, 2000)
}

// ── Create ────────────────────────────────────────────────────────────────────

function openCreate() {
  form.open = true
  form.label = ''
  form.token_type = 'PUBLIC'
  form.district_id = ''
  form.congregation_id = ''
  form.saving = false
  form.error = ''
  formCongregations.value = []
}

async function onFormDistrictChange() {
  form.congregation_id = ''
  formCongregations.value = []
  if (form.district_id) {
    formCongregations.value = await listCongregations(form.district_id)
  }
}

async function saveToken() {
  if (!form.label.trim() || !form.district_id) return
  form.saving = true
  form.error = ''
  try {
    const created = await createExportToken({
      label: form.label.trim(),
      token_type: form.token_type,
      district_id: form.district_id,
      congregation_id: form.congregation_id || null,
    })
    tokens.value.unshift(created)
    await ensureAllCongregations()
    form.open = false
  } catch (e) {
    form.error = e instanceof Error ? e.message : 'Fehler'
  } finally {
    form.saving = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────

function confirmDelete(t: ExportTokenResponse) {
  deleteTarget.value = t
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deleteExportToken(deleteTarget.value.id)
    tokens.value = tokens.value.filter((t) => t.id !== deleteTarget.value!.id)
    deleteTarget.value = null
  } finally {
    deleting.value = false
  }
}

// Preload congregation names for display
onMounted(ensureAllCongregations)
</script>
