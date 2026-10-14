<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div
    class="flex flex-col items-center justify-center text-center gap-2"
    :class="compact ? 'py-3' : 'py-10'"
    data-testid="empty-state"
  >
    <component
      :is="icon"
      v-if="icon"
      class="text-gray-300 dark:text-gray-600"
      :class="compact ? 'h-6 w-6' : 'h-10 w-10'"
      aria-hidden="true"
    />
    <p class="text-sm text-gray-500 dark:text-gray-400">{{ message }}</p>
    <p v-if="hint" class="text-xs text-gray-400 dark:text-gray-500 max-w-sm">{{ hint }}</p>
    <button
      v-if="actionLabel"
      type="button"
      class="btn-primary mt-2 px-4 py-2"
      @click="emit('action')"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'

withDefaults(
  defineProps<{
    message: string
    hint?: string
    icon?: Component
    /** Renders a call-to-action button emitting `action` when set. */
    actionLabel?: string
    compact?: boolean
  }>(),
  { hint: undefined, icon: undefined, actionLabel: undefined, compact: false },
)

const emit = defineEmits<{ action: [] }>()
</script>
