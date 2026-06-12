<template>
  <span
    class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
    :class="badgeClass"
  >
    <span v-if="status === 'PLANNED'">⏳</span>
    <span v-else>✓</span>
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    status: 'PLANNED' | 'CONFIRMED'
  }>(),
  {},
)

const badgeClass = computed(() => {
  if (props.status === 'PLANNED') {
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300'
  }
  return 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
})

const label = computed(() => {
  if (props.status === 'PLANNED') return 'Geplant'
  return 'Bestätigt'
})
</script>
