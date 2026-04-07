<template>
  <div class="p-6 max-w-5xl">
    <h1 class="text-xl font-semibold text-gray-900 mb-5">Amtstragende</h1>

    <!-- Bezirk wählen -->
    <div class="mb-6">
      <label class="block text-xs font-medium text-gray-500 mb-1">Bezirk</label>
      <select
        v-model="selectedDistrictId"
        class="rounded border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        @change="onDistrictChange"
      >
        <option value="">Bezirk wählen…</option>
        <option v-for="d in districts" :key="d.id" :value="d.id">{{ d.name }}</option>
      </select>
    </div>

    <div v-if="!selectedDistrictId" class="text-sm text-gray-400">Bitte Bezirk wählen.</div>
    <div v-else-if="loading" class="text-sm text-gray-500">Lade…</div>

    <template v-else>
      <div class="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
        <h2 class="mb-1 text-sm font-semibold text-blue-900">Eigene Amtsträger-Zuordnung</h2>
        <p class="mb-3 text-xs text-blue-800/80">
          Verknüpft den aktuell eingeloggten Benutzer mit einem Amtsträger in diesem Bezirk.
        </p>
        <div class="grid gap-3 md:grid-cols-[1fr_auto_auto] md:items-center">
          <select
            v-model="selfSelectedLeaderId"
            class="w-full rounded border border-blue-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Amtsträger auswählen…</option>
            <option v-for="leader in activeLeaderOptions" :key="leader.id" :value="leader.id">
              {{ leader.rank ? `${leader.rank} ` : '' }}{{ leader.name }}
            </option>
          </select>
          <button
            class="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            :disabled="!selfSelectedLeaderId || selfLinkLoading"
            @click="connectSelfLink"
          >
            {{ selfLinkLoading ? 'Verknüpfe…' : 'Mit mir verknüpfen' }}
          </button>
          <button
            class="rounded border border-blue-200 bg-white px-4 py-2 text-sm text-blue-700 hover:bg-blue-100 disabled:opacity-50"
            :disabled="!selfLinkedLeader || selfLinkLoading"
            @click="removeSelfLink"
          >
            Verknüpfung lösen
          </button>
        </div>
        <p v-if="selfLinkedLeader" class="mt-2 text-xs text-blue-900">
          Aktuell verknüpft mit:
          <span class="font-medium">{{ selfLinkedLeader.rank ? `${selfLinkedLeader.rank} ` : '' }}{{ selfLinkedLeader.name }}</span>
          <span class="text-blue-800/70">({{ authStore.user?.email ?? authStore.user?.sub ?? 'aktueller Benutzer' }})</span>
        </p>
        <p v-else class="mt-2 text-xs text-blue-900">Aktuell keine Zuordnung gesetzt.</p>
        <p v-if="selfLinkError" class="mt-2 text-xs text-red-600">{{ selfLinkError }}</p>
      </div>

      <div v-for="section in sections" :key="section.id" class="mb-8">
        <!-- Section header -->
        <div class="flex items-center justify-between mb-2 pb-1.5 border-b border-gray-200">
          <div class="flex items-center gap-2">
            <BuildingOffice2Icon
              v-if="section.congregationId === null"
              class="h-4 w-4 text-indigo-400"
            />
            <HomeModernIcon v-else class="h-4 w-4 text-teal-400" />
            <h2 class="text-sm font-semibold text-gray-700">{{ section.label }}</h2>
            <span class="text-xs text-gray-400">({{ leadersForSection(section.congregationId).length }})</span>
          </div>
          <button
            class="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 px-2 py-1 rounded hover:bg-blue-50"
            @click="openAddModal(section.congregationId)"
          >
            <PlusIcon class="h-3.5 w-3.5" />
            Hinzufügen
          </button>
        </div>

        <!-- Empty state -->
        <div
          v-if="leadersForSection(section.congregationId).length === 0"
          class="text-xs text-gray-400 py-2 pl-1"
        >
          Keine Amtstragende angelegt.
        </div>

        <!-- Leaders table -->
        <div v-else class="border border-gray-200 rounded-lg overflow-hidden">
          <table class="w-full text-sm">
            <thead class="bg-gray-50 text-xs text-gray-500 font-medium">
              <tr>
                <th class="px-4 py-2 text-left">Grad</th>
                <th class="px-4 py-2 text-left">Name</th>
                <th class="px-4 py-2 text-left">Beauftragung</th>
                <th v-if="section.congregationId === null" class="px-4 py-2 text-left">Heimat-Gemeinde</th>
                <th class="px-4 py-2 text-left">E-Mail</th>
                <th class="px-4 py-2 text-left">Telefon</th>
                <th class="px-4 py-2 text-center">Status</th>
                <th class="px-4 py-2 text-right">Aktionen</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr
                v-for="leader in leadersForSection(section.congregationId)"
                :key="leader.id"
                class="hover:bg-gray-50"
                :class="!leader.is_active ? 'opacity-50' : ''"
              >
                <td class="px-4 py-2">
                  <span class="inline-block px-2 py-0.5 rounded text-xs font-mono font-medium bg-blue-50 text-blue-700 border border-blue-100">
                    {{ leader.rank ?? '—' }}
                  </span>
                </td>
                <td class="px-4 py-2 font-medium text-gray-800">{{ leader.name }}</td>
                <td class="px-4 py-2">
                  <span
                    v-if="leader.special_role"
                    class="inline-block px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-100"
                  >
                    {{ leader.special_role }}
                  </span>
                  <span v-else class="text-gray-300">—</span>
                </td>
                <td v-if="section.congregationId === null" class="px-4 py-2 text-gray-500">
                  {{ congregationName(leader.congregation_id) || '—' }}
                </td>
                <td class="px-4 py-2 text-gray-500">{{ leader.email || '—' }}</td>
                <td class="px-4 py-2 text-gray-500">{{ leader.phone || '—' }}</td>
                <td class="px-4 py-2 text-center">
                  <span
                    class="inline-block px-2 py-0.5 rounded text-xs font-medium"
                    :class="leader.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-400'"
                  >
                    {{ leader.is_active ? 'Aktiv' : 'Inaktiv' }}
                  </span>
                </td>
                <td class="px-4 py-2 text-right">
                  <div class="flex items-center justify-end gap-1">
                    <button
                      class="p-1.5 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100"
                      title="Bearbeiten"
                      @click="openEditModal(leader)"
                    >
                      <PencilSquareIcon class="h-4 w-4" />
                    </button>
                    <button
                      class="p-1.5 rounded text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                      title="ICS-Export-Token erstellen"
                      @click="openExportModal(leader)"
                    >
                      <LinkIcon class="h-4 w-4" />
                    </button>
                    <button
                      class="p-1.5 rounded text-gray-400 hover:text-red-600 hover:bg-red-50"
                      title="Löschen"
                      @click="confirmDelete(leader)"
                    >
                      <TrashIcon class="h-4 w-4" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- Add modal -->
    <div
      v-if="addModal.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="addModal.open = false"
    >
      <div class="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-gray-900">Amtstragende:n hinzufügen</h2>
          <button class="p-1 rounded hover:bg-gray-100 text-gray-400" @click="addModal.open = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <div class="mb-4 px-3 py-2 bg-gray-50 rounded text-xs text-gray-500 flex items-center gap-1.5">
          <BuildingOffice2Icon v-if="addModal.congregationId === null" class="h-3.5 w-3.5 text-indigo-400" />
          <HomeModernIcon v-else class="h-3.5 w-3.5 text-teal-400" />
          Ebene:
          <span class="font-medium text-gray-700">
            {{ addModal.congregationId ? congregationName(addModal.congregationId) : 'Bezirksebene' }}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-4 mb-4">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              v-model="addModal.name"
              type="text"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Vor- und Nachname"
              @keyup.enter="saveAdd"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Grad *</label>
            <select
              v-model="addModal.rank"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Grad wählen…</option>
              <option v-for="r in LEADER_RANKS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Besondere Beauftragung</label>
            <select
              v-model="addModal.special_role"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option :value="null">Keine</option>
              <option v-for="sr in SPECIAL_ROLES" :key="sr.value" :value="sr.value">{{ sr.label }}</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">E-Mail</label>
            <input
              v-model="addModal.email"
              type="email"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="optional"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Telefon</label>
            <input
              v-model="addModal.phone"
              type="text"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="optional"
            />
          </div>
        </div>

        <p v-if="addModal.error" class="text-sm text-red-600 mb-3">{{ addModal.error }}</p>

        <div class="flex justify-end gap-3">
          <button
            class="text-sm px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
            @click="addModal.open = false"
          >
            Abbrechen
          </button>
          <button
            class="flex items-center gap-1.5 text-sm px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            :disabled="!addModal.name.trim() || !addModal.rank || saving"
            @click="saveAdd"
          >
            <PlusIcon class="h-4 w-4" />
            {{ saving ? 'Speichern…' : 'Hinzufügen' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Edit modal -->
    <div
      v-if="editModal.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="editModal.open = false"
    >
      <div class="bg-white rounded-lg shadow-xl w-full max-w-lg p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-gray-900">Amtstragende:n bearbeiten</h2>
          <button class="p-1 rounded hover:bg-gray-100 text-gray-400" @click="editModal.open = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <div class="grid grid-cols-2 gap-4 mb-4">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              v-model="editModal.name"
              type="text"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Grad *</label>
            <select
              v-model="editModal.rank"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Grad wählen…</option>
              <option v-for="r in LEADER_RANKS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Besondere Beauftragung</label>
            <select
              v-model="editModal.special_role"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option :value="null">Keine</option>
              <option v-for="sr in SPECIAL_ROLES" :key="sr.value" :value="sr.value">{{ sr.label }}</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Gemeinde</label>
            <select
              v-model="editModal.congregation_id"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option :value="null">Bezirksebene</option>
              <option v-for="c in congregations" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">E-Mail</label>
            <input
              v-model="editModal.email"
              type="email"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Telefon</label>
            <input
              v-model="editModal.phone"
              type="text"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">Notizen</label>
            <textarea
              v-model="editModal.notes"
              rows="2"
              class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <label class="flex items-center gap-2 text-sm mb-4">
          <input v-model="editModal.is_active" type="checkbox" class="rounded" />
          <span class="text-gray-700">Aktiv (für Dienstplan-Zuweisung verfügbar)</span>
        </label>

        <p v-if="editModal.error" class="text-sm text-red-600 mb-3">{{ editModal.error }}</p>

        <div class="flex justify-end gap-3">
          <button
            class="text-sm px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
            @click="editModal.open = false"
          >
            Abbrechen
          </button>
          <button
            class="flex items-center gap-1.5 text-sm px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            :disabled="!editModal.name.trim() || !editModal.rank || saving"
            @click="saveEdit"
          >
            <CheckIcon class="h-4 w-4" />
            {{ saving ? 'Speichern…' : 'Speichern' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ICS Export modal -->
    <div
      v-if="exportModal.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="exportModal.open = false"
    >
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-gray-900">
            ICS-Export: {{ exportModal.leaderRank }} {{ exportModal.leaderName }}
          </h2>
          <button class="p-1 rounded hover:bg-gray-100 text-gray-400" @click="exportModal.open = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <template v-if="exportModal.icsUrl">
          <p class="text-sm text-gray-600 mb-2">Persönliche Kalender-URL (nur zugewiesene Gottesdienste):</p>
          <div class="flex items-center gap-2 mb-1">
            <input
              :value="exportModal.icsUrl"
              readonly
              class="flex-1 border border-gray-300 rounded px-3 py-2 text-xs bg-gray-50 text-gray-700 font-mono"
            />
            <button
              class="shrink-0 text-sm px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              @click="copyUrl"
            >
              Kopieren
            </button>
          </div>
          <p v-if="exportModal.copied" class="text-xs text-green-600">Kopiert!</p>
        </template>

        <template v-else>
          <p class="text-sm text-gray-600 mb-4">
            Erstelle einen persönlichen Kalender-Export-Token. Die URL enthält alle zugewiesenen Gottesdienste.
          </p>
          <p v-if="exportModal.error" class="text-sm text-red-600 mb-3">{{ exportModal.error }}</p>
          <div class="flex justify-end gap-3">
            <button
              class="text-sm px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              @click="exportModal.open = false"
            >
              Abbrechen
            </button>
            <button
              class="text-sm px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              :disabled="saving"
              @click="createExportToken"
            >
              Token erstellen
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  BuildingOffice2Icon,
  CheckIcon,
  HomeModernIcon,
  LinkIcon,
  PencilSquareIcon,
  PlusIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { listDistricts, listCongregations, type DistrictResponse, type CongregationResponse } from '@/api/districts'
import {
  createLeader,
  deleteLeader,
  getSelfLeaderLink,
  linkSelfToLeader,
  listLeaders,
  unlinkSelfFromLeader,
  updateLeader,
  LEADER_RANKS,
  SPECIAL_ROLES,
  type LeaderRank,
  type LeaderResponse,
  type SpecialRole,
} from '@/api/leaders'
import { createExportToken as apiCreateExportToken } from '@/api/exportTokens'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const districts = ref<DistrictResponse[]>([])
const congregations = ref<CongregationResponse[]>([])
const leaders = ref<LeaderResponse[]>([])
const selectedDistrictId = ref('')
const loading = ref(false)
const saving = ref(false)
const selfLinkLoading = ref(false)
const selfLinkError = ref('')
const selfLinkedLeader = ref<LeaderResponse | null>(null)
const selfSelectedLeaderId = ref('')

// ── Sections ──────────────────────────────────────────────────────────────────

const RANK_ORDER: Record<string, number> = {
  'StAp.': 9,
  'BezAp.': 8,
  'Ap.': 7,
  'Bi.': 6,
  'BÄ': 5,
  'BE': 4,
  'Hi.': 3,
  'Ev.': 2,
  'Pr.': 1,
  'Di.': 0,
}

const sections = computed(() => [
  { id: 'district', label: 'Bezirksebene', congregationId: null as string | null },
  ...congregations.value.map((c) => ({ id: c.id, label: c.name, congregationId: c.id })),
])

const activeLeaderOptions = computed(() => {
  return [...leaders.value]
    .filter((l) => l.is_active)
    .sort((a, b) => a.name.localeCompare(b.name))
})

function leadersForSection(congregationId: string | null): LeaderResponse[] {
  const filtered =
    congregationId === null
      ? leaders.value.filter((l) => l.congregation_id === null)
      : leaders.value.filter((l) => l.congregation_id === congregationId)
  return [...filtered].sort((a, b) => {
    const rankDiff = (RANK_ORDER[b.rank ?? ''] ?? -1) - (RANK_ORDER[a.rank ?? ''] ?? -1)
    if (rankDiff !== 0) return rankDiff
    const roleA = a.special_role ? 1 : 0
    const roleB = b.special_role ? 1 : 0
    if (roleB !== roleA) return roleB - roleA
    return a.name.localeCompare(b.name)
  })
}

function congregationName(id: string | null): string {
  if (!id) return ''
  return congregations.value.find((c) => c.id === id)?.name ?? ''
}

// ── Load ──────────────────────────────────────────────────────────────────────

onMounted(async () => {
  districts.value = await listDistricts()
})

async function onDistrictChange() {
  if (!selectedDistrictId.value) {
    selfLinkedLeader.value = null
    selfSelectedLeaderId.value = ''
    selfLinkError.value = ''
    return
  }
  loading.value = true
  try {
    ;[leaders.value, congregations.value] = await Promise.all([
      listLeaders(selectedDistrictId.value),
      listCongregations(selectedDistrictId.value),
    ])
    await loadSelfLink()
  } finally {
    loading.value = false
  }
}

async function loadSelfLink() {
  if (!selectedDistrictId.value) return
  selfLinkError.value = ''
  try {
    const linked = await getSelfLeaderLink(selectedDistrictId.value)
    selfLinkedLeader.value = linked.leader
    selfSelectedLeaderId.value = linked.leader?.id ?? ''
  } catch (e) {
    selfLinkError.value = e instanceof Error ? e.message : 'Fehler beim Laden der Zuordnung'
  }
}

async function connectSelfLink() {
  if (!selectedDistrictId.value || !selfSelectedLeaderId.value) return
  selfLinkLoading.value = true
  selfLinkError.value = ''
  try {
    const result = await linkSelfToLeader(selectedDistrictId.value, selfSelectedLeaderId.value)
    selfLinkedLeader.value = result.leader
    leaders.value = await listLeaders(selectedDistrictId.value)
  } catch (e) {
    selfLinkError.value = e instanceof Error ? e.message : 'Fehler beim Verknüpfen'
  } finally {
    selfLinkLoading.value = false
  }
}

async function removeSelfLink() {
  if (!selectedDistrictId.value) return
  selfLinkLoading.value = true
  selfLinkError.value = ''
  try {
    await unlinkSelfFromLeader(selectedDistrictId.value)
    selfLinkedLeader.value = null
    selfSelectedLeaderId.value = ''
    leaders.value = await listLeaders(selectedDistrictId.value)
  } catch (e) {
    selfLinkError.value = e instanceof Error ? e.message : 'Fehler beim Lösen'
  } finally {
    selfLinkLoading.value = false
  }
}

// ── Add modal ─────────────────────────────────────────────────────────────────

const addModal = reactive({
  open: false,
  congregationId: null as string | null,
  name: '',
  rank: '' as LeaderRank | '',
  special_role: null as SpecialRole | null,
  email: '',
  phone: '',
  error: '',
})

function openAddModal(congregationId: string | null) {
  addModal.open = true
  addModal.congregationId = congregationId
  addModal.name = ''
  addModal.rank = ''
  addModal.special_role = null
  addModal.email = ''
  addModal.phone = ''
  addModal.error = ''
}

async function saveAdd() {
  if (!addModal.name.trim() || !addModal.rank || !selectedDistrictId.value) return
  saving.value = true
  addModal.error = ''
  try {
    const created = await createLeader(selectedDistrictId.value, {
      name: addModal.name.trim(),
      rank: addModal.rank,
      congregation_id: addModal.congregationId,
      special_role: addModal.special_role,
      email: addModal.email.trim() || null,
      phone: addModal.phone.trim() || null,
    })
    leaders.value = [...leaders.value, created]
    addModal.open = false
  } catch (e) {
    addModal.error = e instanceof Error ? e.message : 'Fehler'
  } finally {
    saving.value = false
  }
}

// ── Edit modal ────────────────────────────────────────────────────────────────

const editModal = reactive({
  open: false,
  leaderId: '',
  name: '',
  rank: '' as LeaderRank | '',
  congregation_id: null as string | null,
  special_role: null as SpecialRole | null,
  email: '',
  phone: '',
  notes: '',
  is_active: true,
  error: '',
})

function openEditModal(leader: LeaderResponse) {
  editModal.open = true
  editModal.leaderId = leader.id
  editModal.name = leader.name
  editModal.rank = leader.rank ?? ''
  editModal.congregation_id = leader.congregation_id
  editModal.special_role = leader.special_role
  editModal.email = leader.email ?? ''
  editModal.phone = leader.phone ?? ''
  editModal.notes = leader.notes ?? ''
  editModal.is_active = leader.is_active
  editModal.error = ''
}

async function saveEdit() {
  if (!editModal.name.trim() || !editModal.rank) return
  saving.value = true
  editModal.error = ''
  try {
    const updated = await updateLeader(selectedDistrictId.value, editModal.leaderId, {
      name: editModal.name.trim(),
      rank: editModal.rank,
      congregation_id: editModal.congregation_id,
      special_role: editModal.special_role,
      email: editModal.email.trim() || null,
      phone: editModal.phone.trim() || null,
      notes: editModal.notes.trim() || null,
      is_active: editModal.is_active,
    })
    const idx = leaders.value.findIndex((l) => l.id === editModal.leaderId)
    if (idx !== -1) leaders.value[idx] = updated
    editModal.open = false
  } catch (e) {
    editModal.error = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────

async function confirmDelete(leader: LeaderResponse) {
  if (!confirm(`Amtstragende:n "${leader.rank ? leader.rank + ' ' : ''}${leader.name}" wirklich löschen?`)) return
  saving.value = true
  try {
    await deleteLeader(selectedDistrictId.value, leader.id)
    leaders.value = leaders.value.filter((l) => l.id !== leader.id)
  } finally {
    saving.value = false
  }
}

// ── ICS Export modal ──────────────────────────────────────────────────────────

const exportModal = reactive({
  open: false,
  leaderId: '',
  leaderName: '',
  leaderRank: '',
  icsUrl: '',
  copied: false,
  error: '',
})

function openExportModal(leader: LeaderResponse) {
  exportModal.open = true
  exportModal.leaderId = leader.id
  exportModal.leaderName = leader.name
  exportModal.leaderRank = leader.rank ?? ''
  exportModal.icsUrl = ''
  exportModal.copied = false
  exportModal.error = ''
}

async function createExportToken() {
  if (!selectedDistrictId.value) return
  saving.value = true
  exportModal.error = ''
  try {
    const label = exportModal.leaderRank
      ? `${exportModal.leaderRank} ${exportModal.leaderName}`
      : exportModal.leaderName
    const token = await apiCreateExportToken({
      label,
      token_type: 'INTERNAL',
      district_id: selectedDistrictId.value,
      leader_id: exportModal.leaderId,
    })
    const base = window.location.origin
    exportModal.icsUrl = `${base}/api/v1/export/${token.token}/calendar.ics`
  } catch (e) {
    exportModal.error = e instanceof Error ? e.message : 'Fehler beim Erstellen'
  } finally {
    saving.value = false
  }
}

async function copyUrl() {
  await navigator.clipboard.writeText(exportModal.icsUrl)
  exportModal.copied = true
  setTimeout(() => {
    exportModal.copied = false
  }, 2000)
}
</script>
