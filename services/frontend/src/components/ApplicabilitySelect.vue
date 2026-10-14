<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <fieldset class="space-y-2" :disabled="disabled">
    <legend class="form-label">
      Verteilung an Gemeinden
      <span class="text-gray-400 dark:text-gray-500 font-normal">(optional)</span>
    </legend>

    <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
      <input
        type="checkbox"
        data-testid="applicability-all"
        :checked="allSelected"
        @change="toggleAll(($event.target as HTMLInputElement).checked)"
      />
      Alle Gemeinden des Bezirks
    </label>

    <div
      v-if="congregations.length"
      class="max-h-40 overflow-y-auto rounded border border-gray-200 dark:border-gray-700 p-2 space-y-1"
    >
      <label
        v-for="congregation in congregations"
        :key="congregation.id"
        class="flex items-center gap-2 text-sm"
        :class="allSelected ? 'text-gray-400 dark:text-gray-500' : 'text-gray-700 dark:text-gray-300'"
      >
        <input
          type="checkbox"
          :data-testid="`applicability-${congregation.id}`"
          :checked="allSelected || selectedIds.has(congregation.id)"
          :disabled="allSelected"
          @change="toggleCongregation(congregation.id, ($event.target as HTMLInputElement).checked)"
        />
        {{ congregation.name }}
      </label>
    </div>

    <p class="text-xs text-gray-500 dark:text-gray-400">
      Ohne Auswahl erscheint der Termin nur auf Bezirksebene.
    </p>
  </fieldset>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/** Sentinel understood by the backend: distribute to every congregation (UC-04). */
const ALL = 'all'

interface CongregationOption {
  id: string
  name: string
}

const props = withDefaults(
  defineProps<{
    modelValue: string[]
    congregations: CongregationOption[]
    disabled?: boolean
  }>(),
  { disabled: false },
)

const emit = defineEmits<{ 'update:modelValue': [value: string[]] }>()

const allSelected = computed(() => props.modelValue.includes(ALL))
const selectedIds = computed(() => new Set(props.modelValue))

function toggleAll(checked: boolean) {
  emit('update:modelValue', checked ? [ALL] : [])
}

function toggleCongregation(id: string, checked: boolean) {
  const next = new Set(selectedIds.value)
  if (checked) next.add(id)
  else next.delete(id)
  // Keep the congregation order and drop IDs of congregations that no longer exist.
  emit(
    'update:modelValue',
    props.congregations.map((c) => c.id).filter((congregationId) => next.has(congregationId)),
  )
}
</script>
