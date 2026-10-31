<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
<div
  class="modal-backdrop"
  @click.self="emit('close')"
>
  <div class="modal-panel max-w-md">
    <div class="flex items-center justify-between mb-4">
      <h2 class="modal-title">
        ICS-Export: {{ modal.leaderRank }} {{ modal.leaderName }}
      </h2>
      <button class="modal-close" @click="emit('close')">
        <XMarkIcon class="h-5 w-5" />
      </button>
    </div>

    <template v-if="modal.icsUrl">
      <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">Persönliche Kalender-URL (nur zugewiesene Gottesdienste):</p>
      <div class="flex items-center gap-2 mb-1">
        <input
          :value="modal.icsUrl"
          readonly
          class="flex-1 border border-gray-300 dark:border-gray-600 rounded px-3 py-2 text-xs bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-mono"
        />
        <CopyButton :value="modal.icsUrl" />
      </div>
    </template>

    <template v-else>
      <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Erstelle einen persönlichen Kalender-Export-Token. Die URL enthält alle zugewiesenen Gottesdienste.
      </p>
      <ErrorAlert v-if="modal.error" :message="modal.error" class="mb-3" />
      <div class="flex justify-end gap-3">
        <button
          class="btn-secondary hover:bg-gray-50 dark:hover:bg-gray-800"
          @click="emit('close')"
        >
          Abbrechen
        </button>
        <button
          class="btn-primary px-4 py-2"
          :disabled="saving"
          @click="emit('submit')"
        >
          Token erstellen
        </button>
      </div>
    </template>
  </div>
</div>
</template>

<script setup lang="ts">
import type { ExportModalState } from './modalState'
import { XMarkIcon } from '@heroicons/vue/24/outline'
import CopyButton from '../CopyButton.vue'
import ErrorAlert from '../ErrorAlert.vue'

// The parent owns the form state (reactive object) and the save logic; this
// component only renders it. Aliasing the prop avoids prop-mutation lint noise
// for what is intentionally shared, parent-owned form state.
const props = defineProps<{
  modal: ExportModalState
  saving: boolean
}>()
const modal = props.modal
const emit = defineEmits<{ close: []; submit: [] }>()
</script>
