<template>
  <div class="p-6 max-w-3xl">
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-xl font-semibold text-gray-900 dark:text-gray-100">Bezirke & Gemeinden</h1>
      <button
        class="flex items-center gap-1.5 text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700"
        @click="openNewDistrict"
      >
        <PlusIcon class="h-4 w-4" />
        Neuer Bezirk
      </button>
    </div>

    <div v-if="loadingDistricts" class="text-sm text-gray-500 dark:text-gray-400">Lade…</div>
    <div v-else-if="globalError" class="text-sm text-red-600 dark:text-red-400 mb-4">{{ globalError }}</div>

    <!-- District list -->
    <div class="space-y-4">
      <div
        v-for="district in districts"
        :key="district.id"
        class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
      >
        <!-- District header -->
        <div class="flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800">
          <template v-if="editingDistrictId === district.id">
            <input
              v-model="editName"
              class="border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56 dark:bg-gray-800 dark:text-gray-100"
              @keyup.enter="saveDistrict(district)"
              @keyup.escape="cancelEdit"
            />
            <div class="flex gap-1.5 ml-2">
              <button
                class="p-1.5 rounded text-green-600 hover:bg-green-50 disabled:opacity-40"
                :disabled="!editName.trim() || saving"
                title="Speichern"
                @click="saveDistrict(district)"
              >
                <CheckIcon class="h-4 w-4" />
              </button>
              <button class="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700" title="Abbrechen" @click="cancelEdit">
                <XMarkIcon class="h-4 w-4" />
              </button>
            </div>
          </template>
          <template v-else>
            <div class="flex items-center gap-2">
              <span class="font-medium text-gray-900 dark:text-gray-100">{{ district.name }}</span>
              <span
                v-if="district.state_code"
                class="text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/30 text-blue-700 font-medium"
              >{{ district.state_code }}</span>
            </div>
            <div class="flex items-center gap-1.5">
              <button
                class="p-1.5 rounded text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                title="Bezirk umbenennen"
                @click="startEditDistrict(district)"
              >
                <PencilSquareIcon class="h-4 w-4" />
              </button>
              <button
                class="flex items-center gap-1 text-xs text-blue-600 hover:underline px-2 py-1 rounded hover:bg-blue-50"
                @click="openNewGroup(district.id)"
              >
                <PlusIcon class="h-3.5 w-3.5" />
                Gruppe
              </button>
              <button
                class="flex items-center gap-1 text-xs text-blue-600 hover:underline px-2 py-1 rounded hover:bg-blue-50"
                @click="openNewCongregation(district.id)"
              >
                <PlusIcon class="h-3.5 w-3.5" />
                Gemeinde
              </button>
            </div>
          </template>
        </div>

        <!-- New group inline form -->
        <div
          v-if="newGroupDistrictId === district.id"
          class="px-4 py-2 border-t border-gray-100 dark:border-gray-700 bg-amber-50 dark:bg-amber-900/20 flex items-center gap-2"
        >
          <input
            ref="newGroupInput"
            v-model="newGroupName"
            placeholder="Name der Gruppe"
            class="border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 w-56 dark:bg-gray-800 dark:text-gray-100"
            @keyup.enter="saveGroup(district.id)"
            @keyup.escape="cancelNewGroup"
          />
          <button
            class="p-1.5 rounded text-green-600 hover:bg-green-100 disabled:opacity-40"
            :disabled="!newGroupName.trim() || saving"
            title="Hinzufügen"
            @click="saveGroup(district.id)"
          >
            <CheckIcon class="h-4 w-4" />
          </button>
          <button class="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600" title="Abbrechen" @click="cancelNewGroup">
            <XMarkIcon class="h-4 w-4" />
          </button>
        </div>

        <!-- Groups list (inline editting) -->
        <div v-if="groupsByDistrict[district.id]?.length" class="bg-gray-50/50 dark:bg-gray-800/50 border-t border-gray-100 dark:border-gray-700 px-4 py-2 space-y-1">
          <div v-for="group in groupsByDistrict[district.id]" :key="group.id" class="flex items-center justify-between">
            <template v-if="editingGroupId === group.id">
              <input
                v-model="editGroupName"
                class="border border-gray-300 dark:border-gray-600 rounded px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 w-40 dark:bg-gray-800 dark:text-gray-100"
                @keyup.enter="saveEditGroup(district.id, group)"
                @keyup.escape="editingGroupId = null"
              />
              <div class="flex gap-1">
                <button class="p-1 rounded text-green-600 hover:bg-green-100" @click="saveEditGroup(district.id, group)">
                  <CheckIcon class="h-3 w-3" />
                </button>
                <button class="p-1 rounded text-gray-400 dark:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700" @click="editingGroupId = null">
                  <XMarkIcon class="h-3 w-3" />
                </button>
              </div>
            </template>
            <template v-else>
              <span class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">{{ group.name }}</span>
              <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <!-- Actually the li/div above needs "group" class for hover, let's add it -->
              </div>
              <div class="flex items-center gap-1">
                <button class="p-1 rounded text-gray-300 dark:text-gray-600 hover:text-gray-600" @click="startEditGroup(group)">
                  <PencilSquareIcon class="h-3 w-3" />
                </button>
                <button class="p-1 rounded text-gray-300 dark:text-gray-600 hover:text-red-600" @click="confirmDeleteGroup(district.id, group)">
                  <TrashIcon class="h-3 w-3" />
                </button>
              </div>
            </template>
          </div>
        </div>

        <!-- New congregation inline form -->
        <div
          v-if="newCongregationDistrictId === district.id"
          class="px-4 py-2 border-t border-gray-100 dark:border-gray-700 bg-blue-50 dark:bg-blue-900/20 flex items-center gap-2"
        >
          <input
            ref="newCongInput"
            v-model="newCongName"
            placeholder="Name der Gemeinde"
            class="border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56 dark:bg-gray-800 dark:text-gray-100"
            @keyup.enter="saveCongregation(district.id)"
            @keyup.escape="cancelNewCong"
          />
          <button
            class="p-1.5 rounded text-green-600 hover:bg-green-100 disabled:opacity-40"
            :disabled="!newCongName.trim() || saving"
            title="Hinzufügen"
            @click="saveCongregation(district.id)"
          >
            <CheckIcon class="h-4 w-4" />
          </button>
          <button class="p-1.5 rounded text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600" title="Abbrechen" @click="cancelNewCong">
            <XMarkIcon class="h-4 w-4" />
          </button>
          <span v-if="inlineError" class="text-xs text-red-600 dark:text-red-400">{{ inlineError }}</span>
        </div>

        <!-- Congregation list -->
        <ul v-if="congregationsByDistrict[district.id]?.length" class="divide-y divide-gray-100 dark:divide-gray-700">
          <li
            v-for="cong in congregationsByDistrict[district.id]"
            :key="cong.id"
            class="flex items-center justify-between px-4 py-2"
          >
            <div>
              <span class="text-sm text-gray-700 dark:text-gray-300">{{ cong.name }}</span>
              <span class="ml-2 text-xs text-gray-400 dark:text-gray-500">{{ formatServiceTimes(cong.service_times) }}</span>
            </div>
            <button
              class="p-1.5 rounded text-gray-400 dark:text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              title="Gemeinde bearbeiten"
              @click="openEditCong(district.id, cong)"
            >
              <PencilSquareIcon class="h-4 w-4" />
            </button>
          </li>
        </ul>
        <div v-else-if="!newCongregationDistrictId || newCongregationDistrictId !== district.id" class="px-4 py-2 text-xs text-gray-400 dark:text-gray-500">
          Noch keine Gemeinden.
        </div>
      </div>

      <div v-if="!loadingDistricts && districts.length === 0" class="text-sm text-gray-500 dark:text-gray-400">
        Noch keine Bezirke angelegt.
      </div>
    </div>

    <!-- New district modal -->
    <div
      v-if="newDistrictOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="newDistrictOpen = false"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-sm p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">Neuer Bezirk</h2>
          <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500" @click="newDistrictOpen = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name</label>
        <input
          v-model="newDistrictName"
          type="text"
          class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
          placeholder="z. B. Bezirk Nord"
          @keyup.enter="saveNewDistrict"
        />

        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mt-4 mb-1">
          Bundesland <span class="text-gray-400 dark:text-gray-500 font-normal">(für automatischen Feiertags-Import)</span>
        </label>
        <select
          v-model="newDistrictStateCode"
          class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">Kein Bundesland</option>
          <option v-for="(label, code) in DE_STATES" :key="code" :value="code">
            {{ code }} – {{ label }}
          </option>
        </select>

        <p v-if="modalError" class="text-sm text-red-600 dark:text-red-400 mt-2">{{ modalError }}</p>
        <div class="flex justify-end gap-3 mt-5">
          <button
            class="text-sm px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
            @click="newDistrictOpen = false"
          >
            Abbrechen
          </button>
          <button
            class="flex items-center gap-1.5 text-sm px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            :disabled="!newDistrictName.trim() || saving"
            @click="saveNewDistrict"
          >
            <CheckIcon class="h-4 w-4" />
            {{ saving ? 'Speichern…' : 'Anlegen' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Edit congregation modal -->
    <div
      v-if="editCongModal.open"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="closeEditCong"
    >
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-gray-900 dark:text-gray-100">Gemeinde bearbeiten</h2>
          <button class="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500" @click="closeEditCong">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <!-- Name -->
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name</label>
        <input
          v-model="editCongModal.name"
          type="text"
          class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4 dark:bg-gray-800 dark:text-gray-100"
        />

        <!-- Group (optional) -->
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Gruppe (optional)</label>
        <select
          v-model="editCongModal.groupId"
          class="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-5 dark:bg-gray-800 dark:text-gray-100"
        >
          <option :value="null">Keine Gruppe</option>
          <option
            v-for="g in groupsByDistrict[editCongModal.districtId]"
            :key="g.id"
            :value="g.id"
          >
            {{ g.name }}
          </option>
        </select>

        <!-- Gottesdienst-Zeiten -->
        <div class="flex items-center justify-between mb-2">
          <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Gottesdienst-Zeiten</label>
          <button
            class="flex items-center gap-1 text-xs text-blue-600 hover:underline"
            @click="addServiceTime"
          >
            <PlusIcon class="h-3.5 w-3.5" />
            Hinzufügen
          </button>
        </div>

        <div class="space-y-2 mb-5">
          <div
            v-for="(st, idx) in editCongModal.serviceTimes"
            :key="idx"
            class="flex items-center gap-2"
          >
            <select
              v-model="st.weekday"
              class="border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            >
              <option v-for="wd in WEEKDAYS" :key="wd.value" :value="wd.value">{{ wd.label }}</option>
            </select>
            <input
              v-model="st.time"
              type="time"
              class="border border-gray-300 dark:border-gray-600 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 dark:bg-gray-800 dark:text-gray-100"
            />
            <button
              class="p-1 rounded text-gray-400 dark:text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
              title="Entfernen"
              @click="removeServiceTime(idx)"
            >
              <TrashIcon class="h-4 w-4" />
            </button>
          </div>
          <p v-if="editCongModal.serviceTimes.length === 0" class="text-xs text-gray-400 dark:text-gray-500">
            Keine Gottesdienst-Zeiten konfiguriert.
          </p>
        </div>

        <p v-if="editCongModal.error" class="text-sm text-red-600 dark:text-red-400 mb-3">{{ editCongModal.error }}</p>

        <div class="flex justify-end gap-3">
          <button
            class="text-sm px-4 py-2 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800"
            @click="closeEditCong"
          >
            Abbrechen
          </button>
          <button
            class="flex items-center gap-1.5 text-sm px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            :disabled="!editCongModal.name.trim() || saving"
            @click="saveEditCong"
          >
            <CheckIcon class="h-4 w-4" />
            {{ saving ? 'Speichern…' : 'Speichern' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { CheckIcon, PencilSquareIcon, PlusIcon, TrashIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import {
  createCongregation,
  createDistrict,
  createGroup,
  deleteGroup,
  listCongregations,
  listDistricts,
  listGroups,
  updateCongregation,
  updateDistrict,
  updateGroup,
  type CongregationResponse,
  type CongregationGroupResponse,
  type DistrictResponse,
  type ServiceTime,
} from '@/api/districts'

const DE_STATES: Record<string, string> = {
  BB: 'Brandenburg', BE: 'Berlin', BW: 'Baden-Württemberg', BY: 'Bayern',
  HB: 'Bremen', HE: 'Hessen', HH: 'Hamburg', MV: 'Mecklenburg-Vorpommern',
  NI: 'Niedersachsen', NW: 'Nordrhein-Westfalen', RP: 'Rheinland-Pfalz',
  SH: 'Schleswig-Holstein', SL: 'Saarland', SN: 'Sachsen', ST: 'Sachsen-Anhalt',
  TH: 'Thüringen',
}

const WEEKDAYS = [
  { value: 0, label: 'Mo' },
  { value: 1, label: 'Di' },
  { value: 2, label: 'Mi' },
  { value: 3, label: 'Do' },
  { value: 4, label: 'Fr' },
  { value: 5, label: 'Sa' },
  { value: 6, label: 'So' },
]

const WEEKDAY_LABEL: Record<number, string> = Object.fromEntries(
  WEEKDAYS.map((w) => [w.value, w.label]),
)

function formatServiceTimes(times: ServiceTime[]): string {
  if (!times.length) return ''
  return times.map((st) => `${WEEKDAY_LABEL[st.weekday] ?? st.weekday} ${st.time}`).join(' · ')
}

// ── State ─────────────────────────────────────────────────────────────────────

const districts = ref<DistrictResponse[]>([])
const congregationsByDistrict = reactive<Record<string, CongregationResponse[]>>({})
const groupsByDistrict = reactive<Record<string, CongregationGroupResponse[]>>({})
const loadingDistricts = ref(false)
const globalError = ref('')
const saving = ref(false)
const inlineError = ref('')
const modalError = ref('')

const editingDistrictId = ref<string | null>(null)
const editName = ref('')

const newCongregationDistrictId = ref<string | null>(null)
const newCongName = ref('')
const newCongInput = ref<HTMLInputElement | null>(null)

const newDistrictOpen = ref(false)
const newDistrictName = ref('')
const newDistrictStateCode = ref('')

// ── Edit congregation modal ───────────────────────────────────────────────────

interface EditableServiceTime { weekday: number; time: string }

const editCongModal = reactive({
  open: false,
  districtId: '',
  congregationId: '',
  name: '',
  groupId: '' as string | null,
  serviceTimes: [] as EditableServiceTime[],
  error: '',
})

function openEditCong(districtId: string, cong: CongregationResponse) {
  editCongModal.open = true
  editCongModal.districtId = districtId
  editCongModal.congregationId = cong.id
  editCongModal.name = cong.name
  editCongModal.groupId = cong.group_id
  editCongModal.serviceTimes = cong.service_times.map((st) => ({ ...st }))
  editCongModal.error = ''
}

function closeEditCong() {
  editCongModal.open = false
}

function addServiceTime() {
  editCongModal.serviceTimes.push({ weekday: 6, time: '09:30' })
}

function removeServiceTime(idx: number) {
  editCongModal.serviceTimes.splice(idx, 1)
}

async function saveEditCong() {
  if (!editCongModal.name.trim()) return
  saving.value = true
  editCongModal.error = ''
  try {
    const updated = await updateCongregation(
      editCongModal.districtId,
      editCongModal.congregationId,
      {
        name: editCongModal.name.trim(),
        group_id: editCongModal.groupId || null,
        service_times: editCongModal.serviceTimes.map((st) => ({
          weekday: Number(st.weekday),
          time: st.time,
        })),
      },
    )
    const list = congregationsByDistrict[editCongModal.districtId]
    const idx = list?.findIndex((c) => c.id === editCongModal.congregationId) ?? -1
    if (idx !== -1) list[idx] = updated
    closeEditCong()
  } catch (e) {
    editCongModal.error = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}

// ── Load ──────────────────────────────────────────────────────────────────────

onMounted(loadAll)

async function loadAll() {
  loadingDistricts.value = true
  globalError.value = ''
  try {
    districts.value = await listDistricts()
    await Promise.all(
      districts.value.map(async (d) => {
        congregationsByDistrict[d.id] = await listCongregations(d.id)
        groupsByDistrict[d.id] = await listGroups(d.id)
      }),
    )
  } catch (e) {
    globalError.value = e instanceof Error ? e.message : 'Fehler beim Laden'
  } finally {
    loadingDistricts.value = false
  }
}

// ── Districts ─────────────────────────────────────────────────────────────────

function startEditDistrict(district: DistrictResponse) {
  cancelEdit()
  editingDistrictId.value = district.id
  editName.value = district.name
}

async function saveDistrict(district: DistrictResponse) {
  if (!editName.value.trim()) return
  saving.value = true
  try {
    const updated = await updateDistrict(district.id, { name: editName.value.trim() })
    const idx = districts.value.findIndex((d) => d.id === district.id)
    if (idx !== -1) districts.value[idx] = updated
    cancelEdit()
  } finally {
    saving.value = false
  }
}

function openNewDistrict() {
  newDistrictName.value = ''
  newDistrictStateCode.value = ''
  modalError.value = ''
  newDistrictOpen.value = true
}

async function saveNewDistrict() {
  if (!newDistrictName.value.trim()) return
  saving.value = true
  modalError.value = ''
  try {
    const created = await createDistrict(
      newDistrictName.value.trim(),
      newDistrictStateCode.value || null,
    )
    districts.value.push(created)
    congregationsByDistrict[created.id] = []
    newDistrictOpen.value = false
  } catch (e) {
    modalError.value = e instanceof Error ? e.message : 'Fehler'
  } finally {
    saving.value = false
  }
}

// ── Congregations ─────────────────────────────────────────────────────────────

function openNewCongregation(districtId: string) {
  cancelEdit()
  newCongName.value = ''
  inlineError.value = ''
  newCongregationDistrictId.value = districtId
  nextTick(() => newCongInput.value?.focus())
}

async function saveCongregation(districtId: string) {
  if (!newCongName.value.trim()) return
  saving.value = true
  inlineError.value = ''
  try {
    const created = await createCongregation(districtId, newCongName.value.trim())
    congregationsByDistrict[districtId] = [
      ...(congregationsByDistrict[districtId] ?? []),
      created,
    ].sort((a, b) => a.name.localeCompare(b.name))
    cancelNewCong()
  } catch (e) {
    inlineError.value = e instanceof Error ? e.message : 'Fehler'
  } finally {
    saving.value = false
  }
}

function cancelNewCong() {
  newCongregationDistrictId.value = null
  newCongName.value = ''
  inlineError.value = ''
}

// ── Groups ───────────────────────────────────────────────────────────────────

const newGroupDistrictId = ref<string | null>(null)
const newGroupName = ref('')
const newGroupInput = ref<HTMLInputElement | null>(null)

const editingGroupId = ref<string | null>(null)
const editGroupName = ref('')

function openNewGroup(districtId: string) {
  cancelEdit()
  newGroupName.value = ''
  newGroupDistrictId.value = districtId
  nextTick(() => newGroupInput.value?.focus())
}

async function saveGroup(districtId: string) {
  if (!newGroupName.value.trim()) return
  saving.value = true
  try {
    const created = await createGroup(districtId, newGroupName.value.trim())
    groupsByDistrict[districtId] = [
      ...(groupsByDistrict[districtId] ?? []),
      created,
    ].sort((a, b) => a.name.localeCompare(b.name))
    cancelNewGroup()
  } finally {
    saving.value = false
  }
}

function cancelNewGroup() {
  newGroupDistrictId.value = null
  newGroupName.value = ''
}

function startEditGroup(group: CongregationGroupResponse) {
  editingGroupId.value = group.id
  editGroupName.value = group.name
}

async function saveEditGroup(districtId: string, group: CongregationGroupResponse) {
  if (!editGroupName.value.trim()) return
  saving.value = true
  try {
    const updated = await updateGroup(districtId, group.id, editGroupName.value.trim())
    const list = groupsByDistrict[districtId]
    const idx = list?.findIndex((g) => g.id === group.id) ?? -1
    if (idx !== -1) list[idx] = updated
    editingGroupId.value = null
  } finally {
    saving.value = false
  }
}

async function confirmDeleteGroup(districtId: string, group: CongregationGroupResponse) {
  if (!confirm(`Gruppe "${group.name}" wirklich löschen?`)) return
  saving.value = true
  try {
    await deleteGroup(districtId, group.id)
    groupsByDistrict[districtId] = (groupsByDistrict[districtId] || []).filter((g) => g.id !== group.id)
    // Local state: clear group_id for congregations that were in this group
    congregationsByDistrict[districtId]?.forEach((c) => {
      if (c.group_id === group.id) c.group_id = null
    })
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  editingDistrictId.value = null
  editName.value = ''
  newGroupDistrictId.value = null
  editingGroupId.value = null
}
</script>
