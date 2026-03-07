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
            <template v-if="editingCongId === cong.id">
              <input
                v-model="editName"
                class="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
                @keyup.enter="saveCongregationEdit(district.id, cong)"
                @keyup.escape="cancelEdit"
              />
              <div class="flex gap-1.5 ml-2">
                <button
                  class="p-1.5 rounded text-green-600 hover:bg-green-50 disabled:opacity-40"
                  :disabled="!editName.trim() || saving"
                  title="Speichern"
                  @click="saveCongregationEdit(district.id, cong)"
                >
                  <CheckIcon class="h-4 w-4" />
                </button>
                <button class="p-1.5 rounded text-gray-500 hover:bg-gray-100" title="Abbrechen" @click="cancelEdit">
                  <XMarkIcon class="h-4 w-4" />
                </button>
              </div>
            </template>
            <template v-else>
              <span class="text-sm text-gray-700">{{ cong.name }}</span>
              <button
                class="p-1.5 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100"
                title="Gemeinde umbenennen"
                @click="startEditCong(cong)"
              >
                <PencilSquareIcon class="h-4 w-4" />
              </button>
            </template>
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
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import { CheckIcon, PencilSquareIcon, PlusIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import {
  createCongregation,
  createDistrict,
  listCongregations,
  listDistricts,
  updateCongregation,
  updateDistrict,
  type CongregationResponse,
  type DistrictResponse,
} from '@/api/districts'

const districts = ref<DistrictResponse[]>([])
const congregationsByDistrict = reactive<Record<string, CongregationResponse[]>>({})
const loadingDistricts = ref(false)
const globalError = ref('')
const saving = ref(false)
const inlineError = ref('')
const modalError = ref('')

const editingDistrictId = ref<string | null>(null)
const editingCongId = ref<string | null>(null)
const editName = ref('')

const newCongregationDistrictId = ref<string | null>(null)
const newCongName = ref('')
const newCongInput = ref<HTMLInputElement | null>(null)

const newDistrictOpen = ref(false)
const newDistrictName = ref('')

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

function startEditCong(cong: CongregationResponse) {
  cancelEdit()
  editingCongId.value = cong.id
  editName.value = cong.name
}

async function saveCongregationEdit(districtId: string, cong: CongregationResponse) {
  if (!editName.value.trim()) return
  saving.value = true
  try {
    const updated = await updateCongregation(districtId, cong.id, editName.value.trim())
    const list = congregationsByDistrict[districtId]
    const idx = list?.findIndex((c) => c.id === cong.id) ?? -1
    if (idx !== -1) list[idx] = updated
    cancelEdit()
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  editingDistrictId.value = null
  editingCongId.value = null
  editName.value = ''
}
</script>
