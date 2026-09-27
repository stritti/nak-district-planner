<template>
  <form class="space-y-3" @submit.prevent="submit">
    <div v-if="leaders.length > 1">
      <label class="form-label" for="unavailability-leader">Amtsträger:in</label>
      <select id="unavailability-leader" v-model="leaderId" class="form-input" data-testid="unavailability-leader-select">
        <option value="" disabled>Amtsträger:in wählen…</option>
        <option v-for="leader in leaders" :key="leader.id" :value="leader.id">
          {{ leader.rank ? `${leader.rank} ` : '' }}{{ leader.name }}
        </option>
      </select>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div>
        <label class="form-label" for="unavailability-start">Beginn *</label>
        <input
          id="unavailability-start"
          v-model="startDate"
          type="date"
          class="form-input"
          data-testid="unavailability-start-date"
        />
      </div>
      <div>
        <label class="form-label" for="unavailability-end">Ende *</label>
        <input
          id="unavailability-end"
          v-model="endDate"
          type="date"
          class="form-input"
          data-testid="unavailability-end-date"
        />
      </div>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div>
        <label class="form-label" for="unavailability-reason">Grund *</label>
        <select id="unavailability-reason" v-model="reason" class="form-input" data-testid="unavailability-reason-select">
          <option value="" disabled>Grund wählen…</option>
          <option v-for="r in UNAVAILABILITY_REASONS" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
      </div>
      <div>
        <label class="form-label" for="unavailability-note">Notiz</label>
        <input
          id="unavailability-note"
          v-model="note"
          type="text"
          class="form-input"
          placeholder="optional"
          maxlength="2000"
          data-testid="unavailability-note-input"
        />
      </div>
    </div>
    <p v-if="error" class="text-sm text-red-600 dark:text-red-400" data-testid="unavailability-form-error">
      {{ error }}
    </p>
    <div class="flex justify-end">
      <button
        type="submit"
        class="btn-primary px-4 py-2"
        :disabled="saving"
        data-testid="unavailability-submit"
      >
        {{ saving ? 'Speichern…' : 'Abwesenheit erfassen' }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  UNAVAILABILITY_REASONS,
  type LeaderUnavailabilityCreate,
  type UnavailabilityReason,
} from '../api/leaderUnavailabilities'
import type { LeaderResponse } from '../api/leaders'

const props = defineProps<{
  leaders: LeaderResponse[]
  presetLeaderId?: string | null
  saving?: boolean
}>()

const emit = defineEmits<{
  submit: [body: LeaderUnavailabilityCreate]
}>()

const leaderId = ref('')
const startDate = ref('')
const endDate = ref('')
const reason = ref<UnavailabilityReason | ''>('')
const note = ref('')
const error = ref('')

watch(
  () => [props.presetLeaderId, props.leaders] as const,
  ([preset, availableLeaders]) => {
    if (preset) {
      leaderId.value = preset
    } else if (availableLeaders.length === 1) {
      leaderId.value = availableLeaders[0]!.id
    }
  },
  { immediate: true },
)

function submit() {
  error.value = ''
  if (!leaderId.value) {
    error.value = 'Bitte eine Amtsträger:in wählen.'
    return
  }
  if (!startDate.value || !endDate.value || !reason.value) {
    error.value = 'Bitte Beginn, Ende und Grund angeben.'
    return
  }
  const start = new Date(`${startDate.value}T00:00`)
  const end = new Date(`${endDate.value}T23:59`)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    error.value = 'Ungültiges Datum.'
    return
  }
  if (end <= start) {
    error.value = 'Das Ende muss nach dem Beginn liegen.'
    return
  }
  emit('submit', {
    leader_id: leaderId.value,
    start_at: start.toISOString(),
    end_at: end.toISOString(),
    reason: reason.value,
    note: note.value.trim() || null,
  })
}

function reset() {
  startDate.value = ''
  endDate.value = ''
  reason.value = ''
  note.value = ''
  error.value = ''
}

defineExpose({ reset })
</script>
