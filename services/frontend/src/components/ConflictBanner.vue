<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div
    v-if="conflicts.length > 0"
    class="rounded border p-3"
    :class="hasBlocking
      ? 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700'
      : 'bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700'"
    data-testid="conflict-banner"
    role="alert"
  >
    <div class="flex items-center gap-2 mb-1">
      <component
        :is="hasBlocking ? NoSymbolIcon : ExclamationTriangleIcon"
        class="h-5 w-5 shrink-0"
        :class="hasBlocking
          ? 'text-red-600 dark:text-red-400'
          : 'text-amber-600 dark:text-amber-400'"
      />
      <p
        class="text-sm font-semibold"
        :class="hasBlocking
          ? 'text-red-800 dark:text-red-200'
          : 'text-amber-800 dark:text-amber-200'"
      >
        {{ hasBlocking ? 'Zuweisung blockiert' : 'Konflikte vorhanden' }}
      </p>
    </div>
    <ul class="space-y-1 ml-7">
      <li
        v-for="(conflict, index) in conflicts"
        :key="`${conflict.rule_id}-${index}`"
        class="text-xs"
        :class="conflict.severity === 'WARN'
          ? 'text-amber-700 dark:text-amber-300'
          : 'text-red-700 dark:text-red-300'"
        :data-testid="`conflict-${conflict.rule_id}`"
      >
        {{ conflict.message }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ExclamationTriangleIcon, NoSymbolIcon } from '@heroicons/vue/24/outline'
import type { ConflictItem } from '../api/errors'

const props = defineProps<{
  conflicts: ConflictItem[]
}>()

const hasBlocking = computed(() =>
  props.conflicts.some((conflict) => conflict.severity !== 'WARN' && conflict.severity !== 'PASS'),
)
</script>
