<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
<div class="modal-backdrop" @click.self="emit('close')">
  <form class="modal-panel max-w-md space-y-3" @submit.prevent="emit('submit')">
    <div class="flex items-center justify-between">
      <h2 class="modal-title">Ereignis anlegen</h2>
      <button type="button" class="modal-close" @click="emit('close')"><XMarkIcon class="h-5 w-5" /></button>
    </div>
    <label class="form-label" for="new-event-title">Titel</label>
    <input id="new-event-title" v-model.trim="form.title" class="form-input" maxlength="500" required />
    <label class="form-label" for="new-event-start">Beginn</label>
    <input id="new-event-start" v-model="form.start" type="datetime-local" class="form-input" required />
    <label class="form-label" for="new-event-end">Ende</label>
    <input id="new-event-end" v-model="form.end" type="datetime-local" class="form-input" required />
    <label class="form-label" for="new-event-category">Kategorie</label>
    <input id="new-event-category" v-model.trim="form.category" class="form-input" maxlength="255" />
    <label class="form-label" for="new-event-congregation">Gemeinde</label>
    <select id="new-event-congregation" v-model="form.congregation_id" class="form-input">
      <option value="">Bezirksebene</option>
      <option v-for="c in congregations" :key="c.id" :value="c.id">{{ c.name }}</option>
    </select>
    <label class="form-label" for="new-event-description">Beschreibung</label>
    <textarea id="new-event-description" v-model="form.description" class="form-input" rows="2" />
    <label class="form-label" for="new-event-visibility">Sichtbarkeit</label>
    <select id="new-event-visibility" v-model="form.visibility" class="form-input">
      <option value="PUBLIC">Öffentlich nach Freigabe</option>
      <option value="INTERNAL">Nur intern</option>
    </select>
    <p class="text-xs text-gray-500">Neue Ereignisse werden immer als Entwurf angelegt.</p>
    <p v-if="error" role="alert" class="text-sm text-red-600">{{ error }}</p>
    <div class="flex justify-end gap-2">
      <button type="button" class="btn-secondary px-3" @click="emit('close')">Abbrechen</button>
      <button type="submit" class="btn-primary px-3" :disabled="saving">{{ saving ? 'Speichern…' : 'Anlegen' }}</button>
    </div>
  </form>
</div>
</template>

<script setup lang="ts">
import { XMarkIcon } from '@heroicons/vue/24/outline'
import type { CongregationResponse } from '../../api/districts'

export interface EventCreateForm {
  title: string
  start: string
  end: string
  category: string
  congregation_id: string
  description: string
  visibility: 'PUBLIC' | 'INTERNAL'
}

// Parent owns the reactive form and the submit logic; alias avoids prop-mutation noise.
const props = defineProps<{
  form: EventCreateForm
  congregations: CongregationResponse[]
  error: string
  saving: boolean
}>()
const form = props.form
const emit = defineEmits<{ close: []; submit: [] }>()
</script>
