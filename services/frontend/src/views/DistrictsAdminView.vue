<template>
  <div class="p-6 max-w-3xl">
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-xl font-semibold text-gray-900">Bezirke & Gemeinden</h1>
      <button
        class="flex items-center gap-1.5 text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700"
        @click="openNewDistrict"
      >
        <PlusIcon class="h-4 w-4" />
        Neuer Bezirk
      </button>
    </div>

    <div v-if="loadingDistricts" class="text-sm text-gray-500">Lade…</div>
    <div v-else-if="globalError" class="text-sm text-red-600 mb-4">{{ globalError }}</div>

    <!-- District list -->
    <div class="space-y-4">
      <div
        v-for="district in districts"
        :key="district.id"
        class="border border-gray-200 rounded-lg overflow-hidden"
      >
        <!-- District header -->
        <div class="flex items-center justify-between px-4 py-3 bg-gray-50">
          <template v-if="editingDistrictId === district.id">
            <input
              v-model="editName"
              class="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
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
              <button class="p-1.5 rounded text-gray-500 hover:bg-gray-100" title="Abbrechen" @click="cancelEdit">
                <XMarkIcon class="h-4 w-4" />
              </button>
            </div>
          </template>
          <template v-else>
            <span class="font-medium text-gray-900">{{ district.name }}</span>
            <div class="flex items-center gap-1.5">
              <button
                class="p-1.5 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-200"
                title="Bezirk umbenennen"
                @click="startEditDistrict(district)"
              >
                <PencilSquareIcon class="h-4 w-4" />
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

        <!-- New congregation inline form -->
        <div
          v-if="newCongregationDistrictId === district.id"
          class="px-4 py-2 border-t border-gray-100 bg-blue-50 flex items-center gap-2"
        >
          <input
            ref="newCongInput"
            v-model="newCongName"
            placeholder="Name der Gemeinde"
            class="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
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
          <button class="p-1.5 rounded text-gray-500 hover:bg-gray-200" title="Abbrechen" @click="cancelNewCong">
            <XMarkIcon class="h-4 w-4" />
          </button>
          <span v-if="inlineError" class="text-xs text-red-600">{{ inlineError }}</span>
        </div>

        <!-- Congregation list -->
        <ul v-if="congregationsByDistrict[district.id]?.length" class="divide-y divide-gray-100">
          <li
            v-for="cong in congregationsByDistrict[district.id]"
            :key="cong.id"
            class="flex items-center justify-between px-4 py-2"
          >
            <div>
              <span class="text-sm text-gray-700">{{ cong.name }}</span>
              <span class="ml-2 text-xs text-gray-400">{{ formatServiceTimes(cong.service_times) }}</span>
            </div>
            <button
              class="p-1.5 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100"
              title="Gemeinde bearbeiten"
              @click="openEditCong(district.id, cong)"
            >
              <PencilSquareIcon class="h-4 w-4" />
            </button>
          </li>
        </ul>
        <div v-else-if="!newCongregationDistrictId || newCongregationDistrictId !== district.id" class="px-4 py-2 text-xs text-gray-400">
          Noch keine Gemeinden.
        </div>
      </div>

      <div v-if="!loadingDistricts && districts.length === 0" class="text-sm text-gray-500">
        Noch keine Bezirke angelegt.
      </div>
    </div>

    <!-- New district modal -->
    <div
      v-if="newDistrictOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="newDistrictOpen = false"
    >
      <div class="bg-white rounded-lg shadow-xl w-full max-w-sm p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-gray-900">Neuer Bezirk</h2>
          <button class="p-1 rounded hover:bg-gray-100 text-gray-400" @click="newDistrictOpen = false">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Name</label>
        <input
          v-model="newDistrictName"
          type="text"
          class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="z. B. Bezirk Nord"
          @keyup.enter="saveNewDistrict"
        />
        <p v-if="modalError" class="text-sm text-red-600 mt-2">{{ modalError }}</p>
        <div class="flex justify-end gap-3 mt-5">
          <button
            class="text-sm px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
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
      <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-gray-900">Gemeinde bearbeiten</h2>
          <button class="p-1 rounded hover:bg-gray-100 text-gray-400" @click="closeEditCong">
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <!-- Name -->
        <label class="block text-sm font-medium text-gray-700 mb-1">Name</label>
        <input
          v-model="editCongModal.name"
          type="text"
          class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-5"
        />

        <!-- Gottesdienst-Zeiten -->
        <div class="flex items-center justify-between mb-2">
          <label class="text-sm font-medium text-gray-700">Gottesdienst-Zeiten</label>
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
              class="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option v-for="wd in WEEKDAYS" :key="wd.value" :value="wd.value">{{ wd.label }}</option>
            </select>
            <input
              v-model="st.time"
              type="time"
              class="border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              class="p-1 rounded text-gray-400 hover:text-red-600 hover:bg-red-50"
              title="Entfernen"
              @click="removeServiceTime(idx)"
            >
              <TrashIcon class="h-4 w-4" />
            </button>
          </div>
          <p v-if="editCongModal.serviceTimes.length === 0" class="text-xs text-gray-400">
            Keine Gottesdienst-Zeiten konfiguriert.
          </p>
        </div>

        <p v-if="editCongModal.error" class="text-sm text-red-600 mb-3">{{ editCongModal.error }}</p>

        <div class="flex justify-end gap-3">
          <button
            class="text-sm px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
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
  listCongregations,
  listDistricts,
  updateCongregation,
  updateDistrict,
  type CongregationResponse,
  type DistrictResponse,
  type ServiceTime,
} from '@/api/districts'

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

// ── Edit congregation modal ───────────────────────────────────────────────────

interface EditableServiceTime { weekday: number; time: string }

const editCongModal = reactive({
  open: false,
  districtId: '',
  congregationId: '',
  name: '',
  serviceTimes: [] as EditableServiceTime[],
  error: '',
})

function openEditCong(districtId: string, cong: CongregationResponse) {
  editCongModal.open = true
  editCongModal.districtId = districtId
  editCongModal.congregationId = cong.id
  editCongModal.name = cong.name
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
    const updated = await updateDistrict(district.id, editName.value.trim())
    const idx = districts.value.findIndex((d) => d.id === district.id)
    if (idx !== -1) districts.value[idx] = updated
    cancelEdit()
  } finally {
    saving.value = false
  }
}

function openNewDistrict() {
  newDistrictName.value = ''
  modalError.value = ''
  newDistrictOpen.value = true
}

async function saveNewDistrict() {
  if (!newDistrictName.value.trim()) return
  saving.value = true
  modalError.value = ''
  try {
    const created = await createDistrict(newDistrictName.value.trim())
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

function cancelEdit() {
  editingDistrictId.value = null
  editName.value = ''
}
</script>
