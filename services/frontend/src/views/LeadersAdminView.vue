<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div class="p-4 sm:p-6 max-w-5xl">
    <h1 class="page-title">Amtstragende</h1>

    <!-- Bezirk wählen -->
    <div class="mb-6">
        <label class="filter-label">Bezirk</label>
        <select
          :value="selectedDistrictId"
          class="form-select"
          @change="requestDistrictChange"
        >
          <option value="">Bezirk wählen…</option>
          <option v-for="d in districtsStore.districts" :key="d.id" :value="d.id">{{ d.name }}</option>
        </select>
      </div>

    <div v-if="!selectedDistrictId" class="text-sm text-gray-400 dark:text-gray-500">Bitte Bezirk wählen.</div>
    <div v-else-if="loading" class="text-sm text-gray-500 dark:text-gray-400">Lade…</div>

    <template v-else>
      <!-- Tab bar -->
      <div class="flex gap-1 mb-6 border-b border-gray-200 overflow-x-auto">
        <button
          class="px-4 py-2 text-sm font-medium rounded-t transition-colors"
          :class="activeTab === 'leaders'
            ? 'border-b-2 border-blue-600 text-blue-600'
            : 'text-gray-500 hover:text-gray-800'"
          @click="returnToLeaders"
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
        <button
          class="px-4 py-2 text-sm font-medium rounded-t transition-colors"
          :class="activeTab === 'unavailabilities'
            ? 'border-b-2 border-blue-600 text-blue-600'
            : 'text-gray-500 hover:text-gray-800'"
          data-testid="unavailability-tab"
          @click="switchToUnavailabilities()"
        >
          Abwesenheiten
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
        <EmptyState
          v-if="leadersForSection(section.congregationId).length === 0"
          message="Keine Amtstragende angelegt."
          compact
        />

        <!-- Leaders: mobile card list (no horizontal scroll needed) -->
        <div v-else class="md:hidden space-y-2">
          <div
            v-for="leader in leadersForSection(section.congregationId)"
            :key="leader.id"
            class="card p-3"
            :class="!leader.is_active ? 'opacity-50' : ''"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span class="inline-block px-2 py-0.5 rounded text-xs font-mono font-medium bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 border border-blue-100 dark:border-blue-800">
                    {{ leader.rank ?? '—' }}
                  </span>
                  <InlineEditableCell
                    :id="'leader-name-mobile-' + leader.id"
                    as="div"
                    class="font-medium text-gray-800 dark:text-gray-200 break-words min-w-0"
                    :value="leader.name"
                    :revision="leader.revision ?? ''"
                    :label="'Name: ' + leader.name"
                    :editable="canInlineEditLeader(leader)"
                    :coordinator="inlineCoordinator"
                    :save="(value, revision) => saveInlineLeader(leader, 'name', value, revision)"
                    :reload="() => reloadInlineLeader(leader, 'name')"
                    required
                    :max-length="255"
                  />
                </div>
                <p v-if="section.congregationId === null" class="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {{ congregationName(leader.congregation_id) || '—' }}
                </p>
                <div class="mt-0.5 flex flex-wrap gap-2 text-xs text-gray-500 dark:text-gray-400">
                  <InlineEditableCell
                    :id="'leader-email-mobile-' + leader.id"
                    as="div"
                    :value="leader.email"
                    :revision="leader.revision ?? ''"
                    :label="'E-Mail: ' + leader.name"
                    :editable="canInlineEditLeader(leader)"
                    :coordinator="inlineCoordinator"
                    :save="(value, revision) => saveInlineLeader(leader, 'email', value, revision)"
                    :reload="() => reloadInlineLeader(leader, 'email')"
                    :max-length="255"
                  />
                  <InlineEditableCell
                    :id="'leader-phone-mobile-' + leader.id"
                    as="div"
                    :value="leader.phone"
                    :revision="leader.revision ?? ''"
                    :label="'Telefon: ' + leader.name"
                    :editable="canInlineEditLeader(leader)"
                    :coordinator="inlineCoordinator"
                    :save="(value, revision) => saveInlineLeader(leader, 'phone', value, revision)"
                    :reload="() => reloadInlineLeader(leader, 'phone')"
                    :max-length="100"
                  />
                </div>
                <p v-if="leader.special_role" class="text-xs text-indigo-600 dark:text-indigo-400 mt-0.5">Beauftragung: {{ leader.special_role }}</p>
              </div>
              <span
                class="badge shrink-0"
                :class="leader.is_active ? 'bg-green-100 dark:bg-green-900/20 text-green-700' : 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500'"
              >
                {{ leader.is_active ? 'Aktiv' : 'Inaktiv' }}
              </span>
            </div>
            <div class="mt-2 flex items-center justify-end gap-1">
              <button class="btn-icon" title="Bearbeiten" @click="openEditModal(leader)">
                <PencilSquareIcon class="h-4 w-4" />
              </button>
              <button
                class="btn-icon hover:text-amber-600 hover:bg-amber-50 dark:hover:text-amber-400"
                title="Abwesenheiten verwalten"
                @click="openUnavailabilitiesFor(leader)"
              >
                <CalendarDaysIcon class="h-4 w-4" />
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
                title="Deaktivieren und ausblenden"
                @click="confirmDelete(leader)"
              >
                <TrashIcon class="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        <!-- Leaders: desktop table -->
        <div v-if="leadersForSection(section.congregationId).length > 0" class="card overflow-hidden hidden md:block">
          <div class="table-scroll">
          <table data-inline-edit-scope class="table-min-w w-full text-sm">
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
                <InlineEditableCell
                  :id="'leader-name-desktop-' + leader.id"
                  class="py-2 font-medium text-gray-800 dark:text-gray-200"
                  :value="leader.name"
                  :revision="leader.revision ?? ''"
                  :label="'Name: ' + leader.name"
                  :editable="canInlineEditLeader(leader)"
                  :coordinator="inlineCoordinator"
                  :save="(value, revision) => saveInlineLeader(leader, 'name', value, revision)"
                    :reload="() => reloadInlineLeader(leader, 'name')"
                  required
                  :max-length="255"
                />
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
                <InlineEditableCell
                  :id="'leader-email-desktop-' + leader.id"
                  class="py-2"
                  :value="leader.email"
                  :revision="leader.revision ?? ''"
                  :label="'E-Mail: ' + leader.name"
                  :editable="canInlineEditLeader(leader)"
                  :coordinator="inlineCoordinator"
                  :save="(value, revision) => saveInlineLeader(leader, 'email', value, revision)"
                    :reload="() => reloadInlineLeader(leader, 'email')"
                    :max-length="255"
                />
                <InlineEditableCell
                  :id="'leader-phone-desktop-' + leader.id"
                  class="py-2"
                  :value="leader.phone"
                  :revision="leader.revision ?? ''"
                  :label="'Telefon: ' + leader.name"
                  :editable="canInlineEditLeader(leader)"
                  :coordinator="inlineCoordinator"
                  :save="(value, revision) => saveInlineLeader(leader, 'phone', value, revision)"
                    :reload="() => reloadInlineLeader(leader, 'phone')"
                    :max-length="100"
                />
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
                      class="btn-icon hover:text-amber-600 hover:bg-amber-50 dark:hover:text-amber-400"
                      title="Abwesenheiten verwalten"
                      @click="openUnavailabilitiesFor(leader)"
                    >
                      <CalendarDaysIcon class="h-4 w-4" />
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
                      title="Deaktivieren und ausblenden"
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
      </div>
    </template>
    <!-- /Leaders tab -->

    <!-- Registrations tab -->
    <template v-else-if="activeTab === 'registrations'">
      <div v-if="regLoading" class="text-sm text-gray-500">Lade Registrierungen…</div>

      <EmptyState
        v-else-if="registrations.length === 0"
        message="Keine Registrierungsanfragen vorhanden."
        compact
      />

      <div v-else class="border border-gray-200 rounded-lg overflow-hidden">
        <div class="table-scroll">
        <table data-inline-edit-scope class="table-min-w w-full text-sm">
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
                <div class="flex items-center gap-1.5">
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
                  <span
                    v-if="reg.status === 'APPROVED' && reg.idp_provision_status"
                    class="inline-block px-2 py-0.5 rounded text-xs font-medium"
                    :class="reg.idp_provision_status === 'FAILED' ? 'bg-red-100 text-red-700' : 'bg-sky-100 text-sky-700'"
                  >
                    IDP: {{ reg.idp_provision_status }}
                  </span>
                </div>
                <p
                  v-if="reg.idp_provision_error"
                  class="text-xs text-red-600 mt-1"
                >
                  {{ reg.idp_provision_error }}
                </p>
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
      </div>
    </template>
    <!-- /Registrations tab -->

    <!-- Unavailabilities tab -->
    <template v-else-if="activeTab === 'unavailabilities'">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2">
          <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Erfasste Abwesenheiten</h2>
          <LeaderUnavailabilityList
            :items="unavailabilitiesStore.items"
            :leaders="leaders"
            :loading="unavailabilitiesStore.loading"
            :preset-leader-id="unavailabilityFilterLeaderId"
            @update:filter-leader-id="unavailabilityFilterLeaderId = $event"
            :can-delete="canManageUnavailabilities"
            @delete="confirmDeleteUnavailability"
          />
        </div>
        <div v-if="canManageUnavailabilities">
          <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Neue Abwesenheit</h2>
          <LeaderUnavailabilityForm
            ref="unavailabilityFormRef"
            :leaders="leaders"
            :preset-leader-id="unavailabilityFilterLeaderId"
            @update:filter-leader-id="unavailabilityFilterLeaderId = $event"
            :saving="unavailabilitySavingDistrictId === selectedDistrictId"
            @submit="saveUnavailability"
          />
        </div>
      </div>
    </template>
    <!-- /Unavailabilities tab -->

    <ApproveRegistrationModal
      v-if="approveModal.open"
      :modal="approveModal"
      :congregations="congregations"
      :saving="saving"
      @close="approveModal.open = false"
      @submit="doApprove"
    />

    <RejectRegistrationModal
      v-if="rejectModal.open"
      :modal="rejectModal"
      :saving="saving"
      @close="rejectModal.open = false"
      @submit="doReject"
    />

    <!-- Delete registration confirm dialog -->
    <ConfirmDialog
      :open="pendingDeleteReg !== null"
      variant="danger"
      title="Registrierung löschen?"
      :message="pendingDeleteReg ? `Die Registrierung von „${pendingDeleteReg.name}“ wird unwiderruflich gelöscht.` : ''"
      confirm-text="Löschen"
      :loading="saving"
      @confirm="executeDeleteReg"
      @cancel="pendingDeleteReg = null"
    />

    <!-- Delete leader confirm dialog -->
    <ConfirmDialog
      :open="pendingDeleteLeader !== null"
      variant="danger"
      title="Amtsträger:in deaktivieren und ausblenden?"
      :message="pendingDeleteLeader ? `„${pendingDeleteLeader.rank ? pendingDeleteLeader.rank + ' ' : ''}${pendingDeleteLeader.name}“ bleibt für historische Dienste erhalten und wird aus normalen Listen entfernt.` : ''"
      confirm-text="Deaktivieren"
      :loading="saving"
      @confirm="executeDeleteLeader"
      @cancel="pendingDeleteLeader = null"
    />

    <!-- Delete unavailability confirm dialog -->
    <ConfirmDialog
      :open="pendingDeleteUnavailability !== null"
      variant="danger"
      title="Abwesenheit löschen?"
      :message="pendingDeleteUnavailability
        ? `Die Abwesenheit vom ${formatUnavailabilityPeriod(pendingDeleteUnavailability)} wird gelöscht.`
        : ''"
      confirm-text="Löschen"
      :loading="unavailabilityDeleting"
      @confirm="executeDeleteUnavailability"
      @cancel="pendingDeleteUnavailability = null"
    />

    <LeaderAddModal
      v-if="addModal.open"
      :modal="addModal"
      :congregation-label="congregationName(addModal.congregationId)"
      :saving="saving"
      @close="addModal.open = false"
      @submit="saveAdd"
    />

    <LeaderEditModal
      v-if="editModal.open"
      :modal="editModal"
      :congregations="congregations"
      :saving="saving"
      @close="editModal.open = false"
      @submit="saveEdit"
    />

    <LeaderExportModal
      v-if="exportModal.open"
      :modal="exportModal"
      :saving="saving"
      @close="exportModal.open = false"
      @submit="createExportToken"
    />
    </template><!-- closes v-else (district selected) -->
  </div>
</template>

<script setup lang="ts">
import { onBeforeRouteLeave } from 'vue-router'
import { computed, onMounted, reactive, ref } from 'vue'
import { useSessionViewSettings, sessionField, sessionText } from '../composables/useSessionViewSettings'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import ApproveRegistrationModal from '../components/leaders/ApproveRegistrationModal.vue'
import LeaderAddModal from '../components/leaders/LeaderAddModal.vue'
import LeaderEditModal from '../components/leaders/LeaderEditModal.vue'
import LeaderExportModal from '../components/leaders/LeaderExportModal.vue'
import RejectRegistrationModal from '../components/leaders/RejectRegistrationModal.vue'
import type {
  AddModalState,
  ApproveModalState,
  EditModalState,
  ExportModalState,
  RejectModalState,
} from '../components/leaders/modalState'
import EmptyState from '../components/EmptyState.vue'
import LeaderUnavailabilityForm from '../components/LeaderUnavailabilityForm.vue'
import LeaderUnavailabilityList from '../components/LeaderUnavailabilityList.vue'
import InlineEditableCell from '../components/InlineEditableCell.vue'
import { useInlineCellCoordinator } from '../composables/useInlineCellCoordinator'
import {
  BuildingOffice2Icon,
  CalendarDaysIcon,
  CheckIcon,
  HomeModernIcon,
  LinkIcon,
  PencilSquareIcon,
  PlusIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { listCongregations, type CongregationResponse } from '../api/districts'
import {
  createLeader,
  deleteLeader,
  getSelfLeaderLink,
  linkSelfToLeader,
  listLeaders,
  unlinkSelfFromLeader,
  updateLeader,
  updateLeaderInline,
  leaderNameFromId,
  type LeaderRank,
  type LeaderResponse,
  type SpecialRole,
} from '../api/leaders'
import { createExportToken as apiCreateExportToken } from '../api/exportTokens'
import {
  approveRegistration,
  deleteRegistration,
  listRegistrations,
  rejectRegistration,
  type RegistrationResponse,
} from '../api/registrations'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import { useLeaderUnavailabilitiesStore } from '../stores/leaderUnavailabilities'
import { useToastStore } from '../stores/toast'
import {
  formatUnavailabilityPeriod,
  type LeaderUnavailabilityCreate,
  type LeaderUnavailabilityResponse,
} from '../api/leaderUnavailabilities'

const authStore = useAuthStore()
const districtsStore = useDistrictsStore()
const toastStore = useToastStore()
const unavailabilitiesStore = useLeaderUnavailabilitiesStore()
const congregations = ref<CongregationResponse[]>([])
const leaders = ref<LeaderResponse[]>([])
const selectedDistrictId = computed({
  get: () => districtsStore.selectedDistrictId,
  set: (value: string) => districtsStore.setSelectedDistrict(value),
})
const loading = ref(false)
const saving = ref(false)
const inlineCoordinator = useInlineCellCoordinator()
onBeforeRouteLeave(() => inlineCoordinator.finish())

function canInlineEditLeader(leader: LeaderResponse): boolean {
  return (authStore.isSuperadmin || authStore.memberships.some((m) =>
    m.scope_type === 'DISTRICT' && m.scope_id === selectedDistrictId.value && ['PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN'].includes(m.role)
  )) &&
    leader.district_id === selectedDistrictId.value &&
    !!leader.revision
}

async function reloadInlineLeader(
  leader: LeaderResponse,
  field: 'name' | 'email' | 'phone',
): Promise<{ value: string | null; revision: string }> {
  const latest = (await listLeaders(leader.district_id)).find((entry) => entry.id === leader.id)
  if (!latest) throw new Error('Amtstragende:r wurde zwischenzeitlich entfernt.')
  if (selectedDistrictId.value === leader.district_id) {
    leaders.value = leaders.value.map((entry) => entry.id === latest.id ? latest : entry)
  }
  return { value: latest[field], revision: latest.revision ?? '' }
}

async function saveInlineLeader(
  leader: LeaderResponse,
  field: 'name' | 'email' | 'phone',
  value: string,
  revision: string,
): Promise<void> {
  const districtId = leader.district_id
  const saved = await updateLeaderInline(
    districtId, leader.id, { [field]: value || null }, revision,
  )
  if (selectedDistrictId.value !== districtId) return
  leaders.value = leaders.value.map((item) => item.id === saved.id ? saved : item)
  // A failed canonical refresh must not turn an already persisted mutation into an error.
  try {
    const current = await listLeaders(districtId)
    if (selectedDistrictId.value === districtId) leaders.value = current
  } catch {
    // The authoritative PATCH response already updated the visible record.
  }
}

const selfLinkedLeader = ref<LeaderResponse | null>(null)
const selfSelectedLeaderId = ref('')
const selfLinkLoading = ref(false)
const selfLinkError = ref('')

// ── Tab state ──────────────────────────────────────────────────────────────────

const activeTab = ref<'leaders' | 'registrations' | 'unavailabilities'>('leaders')

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

async function returnToLeaders() {
  if (await inlineCoordinator.finish()) activeTab.value = 'leaders'
}

async function switchToRegistrations() {
  if (!(await inlineCoordinator.finish())) return
  activeTab.value = 'registrations'
  await loadRegistrations()
}

// ── Unavailabilities ─────────────────────────────────────────────

const unavailabilityFilterLeaderId = ref('')
useSessionViewSettings('leaders', () => authStore.user?.sub ?? null, () => selectedDistrictId.value, {
  leader: sessionField(unavailabilityFilterLeaderId, () => '', sessionText),
})
const unavailabilitySavingDistrictId = ref('')
let districtLoadGeneration = 0
const unavailabilityDeleting = ref(false)
const unavailabilityFormRef = ref<InstanceType<typeof LeaderUnavailabilityForm> | null>(null)
const pendingDeleteUnavailability = ref<LeaderUnavailabilityResponse | null>(null)

const canManageUnavailabilities = computed(() => {
  if (authStore.isSuperadmin) return true
  return authStore.memberships.some(
    (membership) =>
      membership.scope_type === 'DISTRICT' &&
      membership.scope_id === selectedDistrictId.value &&
      ['PLANNER', 'CONGREGATION_ADMIN', 'DISTRICT_ADMIN'].includes(membership.role),
  )
})

function canIncludeInactiveLeaders(districtId: string): boolean {
  return authStore.isSuperadmin || authStore.memberships.some(
    (membership) =>
      membership.role === 'DISTRICT_ADMIN' &&
      membership.scope_type === 'DISTRICT' &&
      membership.scope_id === districtId,
  )
}

async function switchToUnavailabilities(leaderId?: string) {
  if (!(await inlineCoordinator.finish())) return
  activeTab.value = 'unavailabilities'
  if (leaderId !== undefined) unavailabilityFilterLeaderId.value = leaderId
  try {
    await unavailabilitiesStore.fetchUnavailabilities(selectedDistrictId.value)
  } catch (e) {
    toastStore.error('Abwesenheiten konnten nicht geladen werden', e instanceof Error ? e.message : undefined)
  }
}

function openUnavailabilitiesFor(leader: LeaderResponse) {
  switchToUnavailabilities(leader.id)
}

async function saveUnavailability(body: LeaderUnavailabilityCreate) {
  const districtId = selectedDistrictId.value
  if (!districtId || !canManageUnavailabilities.value) return
  const leaderSnapshot = [...leaders.value]
  unavailabilitySavingDistrictId.value = districtId
  try {
    const created = await unavailabilitiesStore.addUnavailability(body)
    if (selectedDistrictId.value === districtId) {
      unavailabilityFormRef.value?.reset()
      toastStore.success(
        'Abwesenheit erfasst',
        `${leaderNameFromId(created.leader_id, leaderSnapshot)}: ${formatUnavailabilityPeriod(created)}`,
      )
    }
  } catch (e) {
    toastStore.error(
      'Abwesenheit konnte nicht erfasst werden',
      e instanceof Error ? e.message : undefined,
    )
  } finally {
    if (unavailabilitySavingDistrictId.value === districtId) unavailabilitySavingDistrictId.value = ''
  }
}

function confirmDeleteUnavailability(item: LeaderUnavailabilityResponse) {
  pendingDeleteUnavailability.value = item
}

async function executeDeleteUnavailability() {
  if (!pendingDeleteUnavailability.value || !selectedDistrictId.value || !canManageUnavailabilities.value) return
  const item = pendingDeleteUnavailability.value
  unavailabilityDeleting.value = true
  try {
    await unavailabilitiesStore.removeUnavailability(item.id)
    pendingDeleteUnavailability.value = null
    toastStore.success('Abwesenheit gelöscht', formatUnavailabilityPeriod(item))
  } catch (e) {
    toastStore.error('Löschen fehlgeschlagen', e instanceof Error ? e.message : undefined)
  } finally {
    unavailabilityDeleting.value = false
  }
}

// Approve modal
const approveModal = reactive<ApproveModalState>({
  open: false,
  registrationId: '',
  name: '',
  email: '',
  role: 'PLANNER' as 'DISTRICT_ADMIN' | 'CONGREGATION_ADMIN' | 'PLANNER' | 'VIEWER',
  scope_type: 'DISTRICT' as 'DISTRICT' | 'CONGREGATION',
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
  approveModal.role = reg.assigned_role ?? 'PLANNER'
  approveModal.scope_type = reg.assigned_scope_type ?? 'DISTRICT'
  approveModal.rank = reg.rank
  approveModal.congregation_id = reg.congregation_id
  approveModal.special_role = reg.special_role
  approveModal.error = ''
}

async function doApprove() {
  saving.value = true
  approveModal.error = ''
  try {
    if (!selectedDistrictId.value) {
      approveModal.error = 'Kein Bezirk ausgewählt.'
      return
    }
    if (approveModal.scope_type === 'CONGREGATION' && !approveModal.congregation_id) {
      approveModal.error = 'Für CONGREGATION muss eine Gemeinde ausgewählt werden.'
      return
    }

    const scopeId =
      approveModal.scope_type === 'DISTRICT' ? selectedDistrictId.value : approveModal.congregation_id

    if (!scopeId) {
      approveModal.error = 'Scope-ID konnte nicht bestimmt werden.'
      return
    }

    const updated = await approveRegistration(selectedDistrictId.value, approveModal.registrationId, {
      role: approveModal.role,
      scope_type: approveModal.scope_type,
      scope_id: scopeId,
      congregation_id: approveModal.congregation_id,
      rank: approveModal.rank as LeaderRank | null,
      special_role: approveModal.special_role as SpecialRole | null,
    })
    const idx = registrations.value.findIndex((r) => r.id === approveModal.registrationId)
    if (idx !== -1) registrations.value[idx] = updated
    approveModal.open = false
    // Refresh leaders list in background so the new leader appears if user switches tab
    listLeaders(
      selectedDistrictId.value,
      canIncludeInactiveLeaders(selectedDistrictId.value),
    ).then((l) => (leaders.value = l))
  } catch (e) {
    approveModal.error = e instanceof Error ? e.message : 'Fehler beim Genehmigen'
  } finally {
    saving.value = false
  }
}

// Reject modal
const rejectModal = reactive<RejectModalState>({
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
    toastStore.success('Registrierung abgelehnt', rejectModal.name)
  } catch (e) {
    rejectModal.error = e instanceof Error ? e.message : 'Fehler beim Ablehnen'
  } finally {
    saving.value = false
  }
}

const pendingDeleteReg = ref<RegistrationResponse | null>(null)

function confirmDeleteReg(reg: RegistrationResponse) {
  pendingDeleteReg.value = reg
}

async function executeDeleteReg() {
  if (!pendingDeleteReg.value) return
  const reg = pendingDeleteReg.value
  saving.value = true
  try {
    await deleteRegistration(selectedDistrictId.value, reg.id)
    registrations.value = registrations.value.filter((r) => r.id !== reg.id)
    pendingDeleteReg.value = null
    toastStore.success('Registrierung gelöscht', reg.name)
  } catch (e) {
    toastStore.error('Löschen fehlgeschlagen', e instanceof Error ? e.message : undefined)
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

async function requestDistrictChange(event: Event) {
  const selector = event.target as HTMLSelectElement
  const requestedDistrict = selector.value
  if (!(await inlineCoordinator.finish())) {
    selector.value = selectedDistrictId.value
    return
  }
  if (requestedDistrict === selectedDistrictId.value) return
  selectedDistrictId.value = requestedDistrict
  await onDistrictChange()
}

async function onDistrictChange() {
  const loadGeneration = ++districtLoadGeneration
  const districtId = selectedDistrictId.value
  pendingDeleteUnavailability.value = null
  unavailabilityFormRef.value?.reset()
  leaders.value = []
  await unavailabilitiesStore.fetchUnavailabilities('')
  if (loadGeneration !== districtLoadGeneration || districtId !== selectedDistrictId.value) return
  if (!districtId) {
    selfLinkedLeader.value = null
    selfSelectedLeaderId.value = ''
    selfLinkError.value = ''
    return
  }
  loading.value = true
  try {
    const [loadedLeaders, loadedCongregations] = await Promise.all([
      listLeaders(districtId, canIncludeInactiveLeaders(districtId)),
      listCongregations(districtId),
    ])
    if (loadGeneration !== districtLoadGeneration || districtId !== selectedDistrictId.value) return
    leaders.value = loadedLeaders
    if (unavailabilityFilterLeaderId.value && !loadedLeaders.some((leader) => leader.id === unavailabilityFilterLeaderId.value)) {
      unavailabilityFilterLeaderId.value = ''
    }
    congregations.value = loadedCongregations
    await loadSelfLink()
    if (loadGeneration !== districtLoadGeneration || districtId !== selectedDistrictId.value) return
    if (activeTab.value === 'unavailabilities') await switchToUnavailabilities()
  } finally {
    if (loadGeneration === districtLoadGeneration) loading.value = false
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
    leaders.value = await listLeaders(
      selectedDistrictId.value,
      canIncludeInactiveLeaders(selectedDistrictId.value),
    )
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
    leaders.value = await listLeaders(
      selectedDistrictId.value,
      canIncludeInactiveLeaders(selectedDistrictId.value),
    )
  } catch (e) {
    selfLinkError.value = e instanceof Error ? e.message : 'Fehler beim Lösen'
  } finally {
    selfLinkLoading.value = false
  }
}

// ── Add modal ─────────────────────────────────────────────────────────────────

const addModal = reactive<AddModalState>({
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
    toastStore.success('Amtsträger:in erstellt', created.name)
  } catch (e) {
    addModal.error = e instanceof Error ? e.message : 'Fehler'
  } finally {
    saving.value = false
  }
}

// ── Edit modal ────────────────────────────────────────────────────────────────

const editModal = reactive<EditModalState>({
  open: false,
  leaderId: '',
  revision: '',
  name: '',
  rank: '' as LeaderRank | '',
  congregation_id: null as string | null,
  special_role: null as SpecialRole | null,
  email: '',
  phone: '',
  notes: '',
  is_active: true,
  hidden_from_lists: false,
  service_end_date: '',
  error: '',
})

function openEditModal(leader: LeaderResponse) {
  editModal.open = true
  editModal.leaderId = leader.id
  editModal.revision = leader.revision ?? ''
  editModal.name = leader.name
  editModal.rank = leader.rank ?? ''
  editModal.congregation_id = leader.congregation_id
  editModal.special_role = leader.special_role
  editModal.email = leader.email ?? ''
  editModal.phone = leader.phone ?? ''
  editModal.notes = leader.notes ?? ''
  editModal.is_active = leader.is_active
  editModal.hidden_from_lists = leader.hidden_from_lists ?? false
  editModal.service_end_date = leader.service_end_date ?? ''
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
      hidden_from_lists: editModal.hidden_from_lists,
      service_end_date: editModal.service_end_date || null,
    }, editModal.revision)
    const idx = leaders.value.findIndex((l) => l.id === editModal.leaderId)
    if (idx !== -1) leaders.value[idx] = updated
    editModal.open = false
    toastStore.success('Amtsträger:in gespeichert', updated.name)
  } catch (e) {
    editModal.error = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}

// ── Delete ────────────────────────────────────────────────────────────────────

const pendingDeleteLeader = ref<LeaderResponse | null>(null)

function confirmDelete(leader: LeaderResponse) {
  pendingDeleteLeader.value = leader
}

async function executeDeleteLeader() {
  if (!pendingDeleteLeader.value) return
  const leader = pendingDeleteLeader.value
  saving.value = true
  try {
    await deleteLeader(selectedDistrictId.value, leader.id)
    leaders.value = leaders.value.filter((l) => l.id !== leader.id)
    pendingDeleteLeader.value = null
    toastStore.success('Amtsträger:in ausgeblendet', leader.name)
  } catch (e) {
    toastStore.error('Ausblenden fehlgeschlagen', e instanceof Error ? e.message : undefined)
  } finally {
    saving.value = false
  }
}

// ── ICS Export modal ──────────────────────────────────────────────────────────

const exportModal = reactive<ExportModalState>({
  open: false,
  leaderId: '',
  leaderName: '',
  leaderRank: '',
  icsUrl: '',
  error: '',
})

function openExportModal(leader: LeaderResponse) {
  exportModal.open = true
  exportModal.leaderId = leader.id
  exportModal.leaderName = leader.name
  exportModal.leaderRank = leader.rank ?? ''
  exportModal.icsUrl = ''
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

</script>
