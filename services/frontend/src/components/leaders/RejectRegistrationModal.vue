<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
<div
  class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
  @click.self="emit('close')"
>
  <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-base font-semibold text-gray-900">Registrierung ablehnen</h2>
      <button class="p-1 rounded hover:bg-gray-100 text-gray-400" @click="emit('close')">
        <XMarkIcon class="h-5 w-5" />
      </button>
    </div>
    <p class="text-sm text-gray-600 mb-4">
      Die Registrierung von <strong>{{ modal.name }}</strong> wird abgelehnt.
    </p>
    <div class="mb-4">
      <label class="form-label">Begründung (optional)</label>
      <textarea
        v-model="modal.reason"
        rows="3"
        class="form-input w-full resize-none"
        placeholder="Grund für die Ablehnung…"
      />
    </div>
    <p v-if="modal.error" class="text-sm text-red-600 mb-3">{{ modal.error }}</p>
    <div class="flex justify-end gap-3">
      <button
        class="text-sm px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
        @click="emit('close')"
      >Abbrechen</button>
      <button
        class="text-sm px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
        :disabled="saving"
        @click="emit('submit')"
      >Ablehnen</button>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import type { RejectModalState } from './modalState'
import { XMarkIcon } from '@heroicons/vue/24/outline'

// The parent owns the form state (reactive object) and the save logic; this
// component only renders it. Aliasing the prop avoids prop-mutation lint noise
// for what is intentionally shared, parent-owned form state.
const props = defineProps<{
  modal: RejectModalState
  saving: boolean
}>()
const modal = props.modal
const emit = defineEmits<{ close: []; submit: [] }>()
</script>
