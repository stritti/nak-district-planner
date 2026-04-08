<template>
  <div class="p-6 max-w-5xl">
    <h1 class="page-title">Amtstragende</h1>

    <!-- Bezirk wählen -->
    <div class="mb-6">
        <label class="filter-label">Bezirk</label>
        <select
          v-model="selectedDistrictId"
          class="form-select"
          @change="onDistrictChange"
        >
          <option value="">Bezirk wählen…</option>
          <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
      </div>

    <div v-if="!selectedDistrictId" class="text-sm text-gray-400 dark:text-gray-500">Bitte Bezirk wählen.</div>
    <div v-else-if="loading" class="text-sm text-gray-500 dark:text-gray-400">Lade…</div>

    <template v-else>
      <!-- Tab bar -->
      <div class="flex gap-1 mb-6 border-b border-gray-200">
        <button
          class="px-4 py-2 text-sm font-medium rounded-t transition-colors"
          :class="activeTab === 'leaders'
            ? 'border-b-2 border-blue-600 text-blue-600'
            : 'text-gray-500 hover:text-gray-800'"
          @click="activeTab = 'leaders'"
        >
          Amtstragende
        </button>
        <button
          class="px-4 py-2 text-sm font-medium rounded-t transition-colors flex items-center gap-1.5"
          :class="activeTab === 'registrations'
            ? 'border-b-2 border-blue-600 text-blue-600'
            : 'text-gray-500 hover:text-gray-800'"
          @click="switchToRegistrations"
        >
          Registrierungen
          <span
            v-if="pendingCount > 0"
            class="inline-flex items-center justify-center h-5 min-w-[1.25rem] px-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700"
          >{{ pendingCount }}</span>
        </button>
      </div>
      <!-- Leaders tab -->
      <template v-if="activeTab === 'leaders'">
      <div v-for="section in sections" :key="section.id" class="mb-8">
        <!-- Section header -->
        <div class="flex items-center justify-between mb-2 pb-1.5 border-b border-gray-200 dark:border-gray-700">
          <div class="flex items-center gap-2">
            <BuildingOffice2Icon
              v-if="section.congregationId === null"
              class="h-4 w-4 text-indigo-400"
            />
            <HomeModernIcon v-else class="h-4 w-4 text-teal-400" />
            <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{{ section.label }}</h2>
            <span class="text-xs text-gray-400 dark:text-gray-500">({{ leadersForSection(section.congregationId).length }})</span>
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
          class="text-xs text-gray-400 dark:text-gray-500 py-2 pl-1"
        >
          Keine Amtstragende angelegt.
        </div>

        <!-- Leaders table -->
        <div v-else class="card overflow-hidden">
          <table class="w-full text-sm">
            <thead class="table-thead">
              <tr>
                <th class="table-th py-2">Grad</th>
                <th class="table-th py-2">Name</th>
                <th class="table-th py-2">Beauftragung</th>
                <th v-if="section.congregationId === null" class="table-th py-2">Heimat-Gemeinde</th>
                <th class="table-th py-2">E-Mail</th>
                <th class="table-th py-2">Telefon</th>
                <th class="table-th py-2 text-center">Status</th>
                <th class="table-th py-2 text-right">Aktionen</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
              <tr
                v-for="leader in leadersForSection(section.congregationId)"
                :key="leader.id"
                class="hover:bg-gray-50 dark:hover:bg-gray-800"
                :class="!leader.is_active ? 'opacity-50' : ''"
              >
                <td class="px-4 py-2">
                  <span class="inline-block px-2 py-0.5 rounded text-xs font-mono font-medium bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-100 dark:border-blue-800">
                    {{ leader.rank ?? '—' }}
                  </span>
                </td>
                <td class="table-td py-2 font-medium text-gray-800 dark:text-gray-200">{{ leader.name }}</td>
                <td class="px-4 py-2">
                  <span
                    v-if="leader.special_role"
                    class="inline-block px-2 py-0.5 rounded text-xs font-medium bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 border border-amber-100 dark:border-amber-800"
                  >
                    {{ leader.special_role }}
                  </span>
                  <span v-else class="text-gray-300 dark:text-gray-600">—</span>
                </td>
                <td v-if="section.congregationId === null" class="table-td py-2">
                  {{ congregationName(leader.congregation_id) || '—' }}
                </td>
                <td class="table-td py-2">{{ leader.email || '—' }}</td>
                <td class="table-td py-2">{{ leader.phone || '—' }}</td>
                <td class="table-td py-2 text-center">
                  <span
                    class="badge"
                    :class="leader.is_active ? 'bg-green-100 dark:bg-green-900/20 text-green-700' : 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500'"
                  >
                    {{ leader.is_active ? 'Aktiv' : 'Inaktiv' }}
                  </span>
                </td>
                <td class="table-td py-2 text-right">
                  <div class="flex items-center justify-end gap-1">
                    <button
                      class="btn-icon"
                      title="Bearbeiten"
                      @click="openEditModal(leader)"
                    >
                      <PencilSquareIcon class="h-4 w-4" />
                    </button>
                    <button
                      class="btn-icon hover:text-blue-600 hover:bg-blue-50 dark:hover:text-blue-400"
                      title="ICS-Export-Token erstellen"
                      @click="openExportModal(leader)"
                    >
                      <LinkIcon class="h-4 w-4" />
                    </button>
                    <button
                      class="btn-icon hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
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
    <!-- /Leaders tab -->

    <!-- Registrations tab -->
    <template v-else-if="activeTab === 'registrations'">
      <div v-if="regLoading" class="text-sm text-gray-500">Lade Registrierungen…</div>

      <div v-else-if="registrations.length === 0" class="text-sm text-gray-400 py-4">
        Keine Registrierungsanfragen vorhanden.
      </div>

      <div v-else class="border border-gray-200 rounded-lg overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-xs text-gray-500 font-medium">
            <tr>
              <th class="px-4 py-2 text-left">Name</th>
              <th class="px-4 py-2 text-left">E-Mail</th>
              <th class="px-4 py-2 text-left">Grad</th>
              <th class="px-4 py-2 text-left">Gemeinde (Wunsch)</th>
              <th class="px-4 py-2 text-left">Status</th>
              <th class="px-4 py-2 text-left">Eingereicht</th>
              <th class="px-4 py-2 text-right">Aktionen</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr
              v-for="reg in registrations"
              :key="reg.id"
              class="hover:bg-gray-50"
            >
              <td class="px-4 py-2 font-medium text-gray-800">{{ reg.name }}</td>
              <td class="px-4 py-2 text-gray-500">{{ reg.email }}</td>
              <td class="px-4 py-2">
                <span v-if="reg.rank" class="inline-block px-2 py-0.5 rounded text-xs font-mono font-medium bg-blue-50 text-blue-700 border border-blue-100">
                  {{ reg.rank }}
                </span>
                <span v-else class="text-gray-300">—</span>
              </td>
              <td class="px-4 py-2 text-gray-500">{{ congregationName(reg.congregation_id) || '—' }}</td>
              <td class="px-4 py-2">
                <span
                  class="inline-block px-2 py-0.5 rounded text-xs font-medium"
                  :class="{
                    'bg-amber-100 text-amber-700': reg.status === 'PENDING',
                    'bg-green-100 text-green-700': reg.status === 'APPROVED',
                    'bg-red-100 text-red-600': reg.status === 'REJECTED',
                  }"
                >
                  {{ { PENDING: 'Ausstehend', APPROVED: 'Genehmigt', REJECTED: 'Abgelehnt' }[reg.status] }}
                </span>
              </td>
              <td class="px-4 py-2 text-gray-400 text-xs">
                {{ new Date(reg.created_at).toLocaleDateString('de-DE') }}
              </td>
              <td class="px-4 py-2">
                <div class="flex items-center justify-end gap-1">
                  <template v-if="reg.status === 'PENDING'">
                    <button
                      class="flex items-center gap-1 text-xs text-green-700 hover:text-green-900 px-2 py-1 rounded hover:bg-green-50"
                      title="Genehmigen"
                      @click="openApproveModal(reg)"
                    >
                      <CheckIcon class="h-3.5 w-3.5" />
                      Genehmigen
                    </button>
                    <button
                      class="flex items-center gap-1 text-xs text-red-600 hover:text-red-800 px-2 py-1 rounded hover:bg-red-50"
                      title="Ablehnen"
                      @click="openRejectModal(reg)"
                    >
                      <XMarkIcon class="h-3.5 w-3.5" />
                      Ablehnen
                    </button>
                  </template>
                  <button
                    class="p-1 rounded text-gray-300 hover:text-red-500 hover:bg-red-50"
                    title="Löschen"
                    @click="confirmDeleteReg(reg)"
                  >
                    <TrashIcon class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
    <!-- /Registrations tab -->

    <!-- Approve registration modal -->
    <div
      v-if="approveModal.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="approveModal.open = false"
    >
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-gray-900">Registrierung genehmigen</h2>
          <button class="p-1 rounded hover:bg-gray-100 text-gray-400" @click="approveModal.open = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <p class="text-sm text-gray-600 mb-4">
          <strong>{{ approveModal.name }}</strong> ({{ approveModal.email }}) wird als Amtstragende:r hinzugefügt.
          Sie können Grad und Gemeinde vor der Genehmigung anpassen.
        </p>
        <div class="space-y-3 mb-4">
          <div>
            <label class="form-label">Grad</label>
            <select v-model="approveModal.rank" class="form-select w-full">
              <option :value="null">— kein Grad —</option>
              <option v-for="r in LEADER_RANKS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
          <div>
            <label class="form-label">Gemeinde</label>
            <select v-model="approveModal.congregation_id" class="form-select w-full">
              <option :value="null">— Bezirksebene —</option>
              <option v-for="c in congregations" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div>
            <label class="form-label">Beauftragung</label>
            <select v-model="approveModal.special_role" class="form-select w-full">
              <option :value="null">— keine —</option>
              <option v-for="r in SPECIAL_ROLES" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
        </div>
        <p v-if="approveModal.error" class="text-sm text-red-600 mb-3">{{ approveModal.error }}</p>
        <div class="flex justify-end gap-3">
          <button
            class="text-sm px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
            @click="approveModal.open = false"
          >Abbrechen</button>
          <button
            class="text-sm px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            :disabled="saving"
            @click="doApprove"
          >Genehmigen</button>
        </div>
      </div>
    </div>

    <!-- Reject registration modal -->
    <div
      v-if="rejectModal.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="rejectModal.open = false"
    >
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-gray-900">Registrierung ablehnen</h2>
          <button class="p-1 rounded hover:bg-gray-100 text-gray-400" @click="rejectModal.open = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <p class="text-sm text-gray-600 mb-4">
          Die Registrierung von <strong>{{ rejectModal.name }}</strong> wird abgelehnt.
        </p>
        <div class="mb-4">
          <label class="form-label">Begründung (optional)</label>
          <textarea
            v-model="rejectModal.reason"
            rows="3"
            class="form-input w-full resize-none"
            placeholder="Grund für die Ablehnung…"
          />
        </div>
        <p v-if="rejectModal.error" class="text-sm text-red-600 mb-3">{{ rejectModal.error }}</p>
        <div class="flex justify-end gap-3">
          <button
            class="text-sm px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
            @click="rejectModal.open = false"
          >Abbrechen</button>
          <button
            class="text-sm px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            :disabled="saving"
            @click="doReject"
          >Ablehnen</button>
        </div>
      </div>
    </div>

    <div
      v-if="addModal.open"
      class="modal-backdrop"
      @click.self="addModal.open = false"
    >
      <div class="modal-panel max-w-lg">
        <div class="flex items-center justify-between mb-4">
          <h2 class="modal-title">Amtstragende:n hinzufügen</h2>
          <button class="modal-close" @click="addModal.open = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <div class="mb-4 px-3 py-2 bg-gray-50 dark:bg-gray-800 rounded text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
          <BuildingOffice2Icon v-if="addModal.congregationId === null" class="h-3.5 w-3.5 text-indigo-400" />
          <HomeModernIcon v-else class="h-3.5 w-3.5 text-teal-400" />
          Ebene:
          <span class="font-medium text-gray-700 dark:text-gray-300">
            {{ addModal.congregationId ? congregationName(addModal.congregationId) : 'Bezirksebene' }}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-4 mb-4">
          <div class="col-span-2">
            <label class="form-label">Name *</label>
            <input
              v-model="addModal.name"
              type="text"
              class="form-input"
              placeholder="Vor- und Nachname"
              @keyup.enter="saveAdd"
            />
          </div>

          <div>
            <label class="form-label">Grad *</label>
            <select
              v-model="addModal.rank"
              class="form-input"
            >
              <option value="">Grad wählen…</option>
              <option v-for="r in LEADER_RANKS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>

          <div>
            <label class="form-label">Besondere Beauftragung</label>
            <select
              v-model="addModal.special_role"
              class="form-input"
            >
              <option :value="null">Keine</option>
              <option v-for="sr in SPECIAL_ROLES" :key="sr.value" :value="sr.value">{{ sr.label }}</option>
            </select>
          </div>

          <div>
            <label class="form-label">E-Mail</label>
            <input
              v-model="addModal.email"
              type="email"
              class="form-input"
              placeholder="optional"
            />
          </div>

          <div>
            <label class="form-label">Telefon</label>
            <input
              v-model="addModal.phone"
              type="text"
              class="form-input"
              placeholder="optional"
            />
          </div>
        </div>

        <p v-if="addModal.error" class="text-sm text-red-600 dark:text-red-400 mb-3">{{ addModal.error }}</p>

        <div class="flex justify-end gap-3">
          <button
            class="btn-secondary hover:bg-gray-50 dark:hover:bg-gray-800"
            @click="addModal.open = false"
          >
            Abbrechen
          </button>
          <button
            class="btn-primary px-4 py-2"
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
      class="modal-backdrop"
      @click.self="editModal.open = false"
    >
      <div class="modal-panel max-w-lg">
        <div class="flex items-center justify-between mb-4">
          <h2 class="modal-title">Amtstragende:n bearbeiten</h2>
          <button class="modal-close" @click="editModal.open = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <div class="grid grid-cols-2 gap-4 mb-4">
          <div class="col-span-2">
            <label class="form-label">Name *</label>
            <input
              v-model="editModal.name"
              type="text"
              class="form-input"
            />
          </div>

          <div>
            <label class="form-label">Grad *</label>
            <select
              v-model="editModal.rank"
              class="form-input"
            >
              <option value="">Grad wählen…</option>
              <option v-for="r in LEADER_RANKS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>

          <div>
            <label class="form-label">Besondere Beauftragung</label>
            <select
              v-model="editModal.special_role"
              class="form-input"
            >
              <option :value="null">Keine</option>
              <option v-for="sr in SPECIAL_ROLES" :key="sr.value" :value="sr.value">{{ sr.label }}</option>
            </select>
          </div>

          <div>
            <label class="form-label">Gemeinde</label>
            <select
              v-model="editModal.congregation_id"
              class="form-input"
            >
              <option :value="null">Bezirksebene</option>
              <option v-for="c in congregations" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>

          <div>
            <label class="form-label">E-Mail</label>
            <input
              v-model="editModal.email"
              type="email"
              class="form-input"
            />
          </div>

          <div>
            <label class="form-label">Telefon</label>
            <input
              v-model="editModal.phone"
              type="text"
              class="form-input"
            />
          </div>

          <div class="col-span-2">
            <label class="form-label">Notizen</label>
            <textarea
              v-model="editModal.notes"
              rows="2"
              class="form-input"
            />
          </div>
        </div>

        <label class="flex items-center gap-2 text-sm mb-4">
          <input v-model="editModal.is_active" type="checkbox" class="rounded" />
          <span class="text-gray-700 dark:text-gray-300">Aktiv (für Dienstplan-Zuweisung verfügbar)</span>
        </label>

        <p v-if="editModal.error" class="text-sm text-red-600 dark:text-red-400 mb-3">{{ editModal.error }}</p>

        <div class="flex justify-end gap-3">
          <button
            class="btn-secondary hover:bg-gray-50 dark:hover:bg-gray-800"
            @click="editModal.open = false"
          >
            Abbrechen
          </button>
          <button
            class="btn-primary px-4 py-2"
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
      class="modal-backdrop"
      @click.self="exportModal.open = false"
    >
      <div class="modal-panel max-w-md">
        <div class="flex items-center justify-between mb-4">
          <h2 class="modal-title">
            ICS-Export: {{ exportModal.leaderRank }} {{ exportModal.leaderName }}
          </h2>
          <button class="modal-close" @click="exportModal.open = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <template v-if="exportModal.icsUrl">
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">Persönliche Kalender-URL (nur zugewiesene Gottesdienste):</p>
          <div class="flex items-center gap-2 mb-1">
            <input
              :value="exportModal.icsUrl"
              readonly
              class="flex-1 border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-xs bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-mono"
            />
            <button
              class="btn-primary shrink-0 px-3 py-2"
              @click="copyUrl"
            >
              Kopieren
            </button>
          </div>
          <p v-if="exportModal.copied" class="text-xs text-green-600">Kopiert!</p>
        </template>

        <template v-else>
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Erstelle einen persönlichen Kalender-Export-Token. Die URL enthält alle zugewiesenen Gottesdienste.
          </p>
          <p v-if="exportModal.error" class="text-sm text-red-600 dark:text-red-400 mb-3">{{ exportModal.error }}</p>
          <div class="flex justify-end gap-3">
            <button
              class="btn-secondary hover:bg-gray-50 dark:hover:bg-gray-800"
              @click="exportModal.open = false"
            >
              Abbrechen
            </button>
            <button
              class="btn-primary px-4 py-2"
              :disabled="saving"
              @click="createExportToken"
            >
              Token erstellen
            </button>
          </div>
        </template>
      </div>
    </div>
    </template><!-- closes v-else (district selected) -->
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
import { listCongregations, type CongregationResponse } from '@/api/districts'
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
import {
  approveRegistration,
  deleteRegistration,
  listRegistrations,
  rejectRegistration,
  type RegistrationResponse,
} from '@/api/registrations'
import { useDistrictsStore } from '@/stores/districts'

const districtsStore = useDistrictsStore()
const congregations = ref<CongregationResponse[]>([])
const leaders = ref<LeaderResponse[]>([])
const selectedDistrictId = computed({
  get: () => districtsStore.selectedDistrictId,
  set: (value: string) => districtsStore.setSelectedDistrict(value),
})
const loading = ref(false)
const saving = ref(false)

const selfLinkedLeader = ref<LeaderResponse | null>(null)
const selfSelectedLeaderId = ref('')
const selfLinkLoading = ref(false)
const selfLinkError = ref('')

// ── Tab state ──────────────────────────────────────────────────────────────────

const activeTab = ref<'leaders' | 'registrations'>('leaders')

// ── Registrations ─────────────────────────────────────────────────────────────

const registrations = ref<RegistrationResponse[]>([])
const regLoading = ref(false)

const pendingCount = computed(
  () => registrations.value.filter((r) => r.status === 'PENDING').length,
)

async function loadRegistrations() {
  if (!selectedDistrictId.value) return
  regLoading.value = true
  try {
    registrations.value = await listRegistrations(selectedDistrictId.value)
  } finally {
    regLoading.value = false
  }
}

async function switchToRegistrations() {
  activeTab.value = 'registrations'
  await loadRegistrations()
}

// Approve modal
const approveModal = reactive({
  open: false,
  registrationId: '',
  name: '',
  email: '',
  rank: null as string | null,
  congregation_id: null as string | null,
  special_role: null as string | null,
  error: '',
})

function openApproveModal(reg: RegistrationResponse) {
  approveModal.open = true
  approveModal.registrationId = reg.id
  approveModal.name = reg.name
  approveModal.email = reg.email
  approveModal.rank = reg.rank
  approveModal.congregation_id = reg.congregation_id
  approveModal.special_role = reg.special_role
  approveModal.error = ''
}

async function doApprove() {
  saving.value = true
  approveModal.error = ''
  try {
    const updated = await approveRegistration(selectedDistrictId.value, approveModal.registrationId, {
      congregation_id: approveModal.congregation_id,
      rank: approveModal.rank as LeaderRank | null,
      special_role: approveModal.special_role as SpecialRole | null,
    })
    const idx = registrations.value.findIndex((r) => r.id === approveModal.registrationId)
    if (idx !== -1) registrations.value[idx] = updated
    approveModal.open = false
    // Refresh leaders list in background so the new leader appears if user switches tab
    listLeaders(selectedDistrictId.value).then((l) => (leaders.value = l))
  } catch (e) {
    approveModal.error = e instanceof Error ? e.message : 'Fehler beim Genehmigen'
  } finally {
    saving.value = false
  }
}

// Reject modal
const rejectModal = reactive({
  open: false,
  registrationId: '',
  name: '',
  reason: '',
  error: '',
})

function openRejectModal(reg: RegistrationResponse) {
  rejectModal.open = true
  rejectModal.registrationId = reg.id
  rejectModal.name = reg.name
  rejectModal.reason = ''
  rejectModal.error = ''
}

async function doReject() {
  saving.value = true
  rejectModal.error = ''
  try {
    const updated = await rejectRegistration(selectedDistrictId.value, rejectModal.registrationId, {
      reason: rejectModal.reason || null,
    })
    const idx = registrations.value.findIndex((r) => r.id === rejectModal.registrationId)
    if (idx !== -1) registrations.value[idx] = updated
    rejectModal.open = false
  } catch (e) {
    rejectModal.error = e instanceof Error ? e.message : 'Fehler beim Ablehnen'
  } finally {
    saving.value = false
  }
}

async function confirmDeleteReg(reg: RegistrationResponse) {
  if (!confirm(`Registrierung von "${reg.name}" wirklich löschen?`)) return
  saving.value = true
  try {
    await deleteRegistration(selectedDistrictId.value, reg.id)
    registrations.value = registrations.value.filter((r) => r.id !== reg.id)
  } finally {
    saving.value = false
  }
}

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
  await districtsStore.fetchDistricts()
  if (selectedDistrictId.value) {
    await onDistrictChange()
  }
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
