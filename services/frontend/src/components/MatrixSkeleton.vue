<template>
  <div
    role="status"
    aria-busy="true"
    aria-live="polite"
    class="overflow-hidden rounded border border-gray-200 dark:border-gray-700"
    data-testid="matrix-skeleton"
  >
    <span class="sr-only">Dienstplan wird geladen…</span>
    <div class="animate-pulse" aria-hidden="true">
      <div class="flex gap-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 p-2">
        <div class="h-4 w-36 shrink-0 rounded bg-gray-200 dark:bg-gray-700" />
        <div v-for="col in columns" :key="col" class="h-4 flex-1 rounded bg-gray-200 dark:bg-gray-700" />
      </div>
      <div
        v-for="row in rows"
        :key="row"
        class="flex gap-2 border-b border-gray-100 dark:border-gray-800 p-2 last:border-b-0"
        data-testid="matrix-skeleton-row"
      >
        <div class="h-8 w-36 shrink-0 rounded bg-gray-200 dark:bg-gray-700" />
        <div v-for="col in columns" :key="col" class="h-8 flex-1 rounded bg-gray-100 dark:bg-gray-800" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ rows?: number; columns?: number }>(), { rows: 6, columns: 5 })
</script>
