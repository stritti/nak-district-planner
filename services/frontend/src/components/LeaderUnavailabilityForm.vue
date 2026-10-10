<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <form class="space-y-3" @submit.prevent="submit">
    <p v-if="leaders.length === 0" class="text-sm text-gray-500 dark:text-gray-400" data-testid="unavailability-no-leaders">
      Keine Amtsträger:innen vorhanden. Bitte zuerst Amtsträger:innen anlegen.
    </p>
    <template v-else>
      <div v-if="leaders.length > 1">
        <label class="form-label" for="unavailability-leader">Amtsträger:in *</label>
        <select id="unavailability-leader" v-model="leaderId" class="form-input" :aria-invalid="!!error" data-testid="unavailability-leader-select" :disabled="saving">
          <option value="" disabled>Amtsträger:in wählen…</option>
          <option v-for="leader in leaders" :key="leader.id" :value="leader.id">
            {{ leaderDisplayName(leader) }}
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
            required
            aria-required="true"
            :aria-invalid="!!error"
            class="form-input"
            data-testid="unavailability-start-date"
            :disabled="saving"
          />
        </div>
        <div>
          <label class="form-label" for="unavailability-end">Ende *</label>
          <input
            id="unavailability-end"
            v-model="endDate"
            type="date"
            required
            aria-required="true"
            :aria-invalid="!!error"
            class="form-input"
            data-testid="unavailability-end-date"
            :disabled="saving"
          />
        </div>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label class="form-label" for="unavailability-reason">Grund *</label>
          <select id="unavailability-reason" v-model="reason" required :aria-invalid="!!error" class="form-input" data-testid="unavailability-reason-select" :disabled="saving">
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
            :disabled="saving"
          />
        </div>
      </div>
      <p v-if="error" class="text-sm text-red-600 dark:text-red-400" role="alert" aria-live="polite" data-testid="unavailability-form-error">
        {{ error }}
      </p>
      <div class="flex justify-end">
        <button
          type="submit"
          class="btn-primary px-4 py-2"
          :disabled="saving || leaders.length === 0"
          data-testid="unavailability-submit"
        >
          {{ saving ? 'Speichern…' : 'Abwesenheit erfassen' }}
        </button>
      </div>
    </template>
  </form>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  UNAVAILABILITY_REASONS,
  planningDayBounds,
  type LeaderUnavailabilityCreate,
  type UnavailabilityReason,
} from '../api/leaderUnavailabilities'
import type { LeaderResponse } from '../api/leaders'
import { leaderDisplayName } from '../api/leaders'

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
    if (preset && availableLeaders.some((leader) => leader.id === preset)) {
      leaderId.value = preset
    } else if (availableLeaders.length === 1) {
      leaderId.value = availableLeaders[0]!.id
    } else if (!availableLeaders.some((leader) => leader.id === leaderId.value)) {
      leaderId.value = ''
    }
  },
  { immediate: true },
)

function submit() {
  if (props.saving) return
  error.value = ''
  if (!props.leaders.some((leader) => leader.id === leaderId.value)) {
    error.value = 'Bitte eine Amtsträger:in wählen.'
    return
  }
  if (!startDate.value || !endDate.value || !reason.value) {
    error.value = 'Bitte Beginn, Ende und Grund angeben.'
    return
  }
  if (endDate.value < startDate.value) {
    error.value = 'Das Ende muss nach dem Beginn liegen.'
    return
  }
  let start: string
  let end: string
  try {
    start = planningDayBounds(startDate.value).start
    end = planningDayBounds(endDate.value).end
  } catch {
    error.value = 'Ungültiges Datum.'
    return
  }
  emit('submit', {
    leader_id: leaderId.value,
    start_at: start,
    end_at: end,
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
