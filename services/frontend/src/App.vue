<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950">
    <AppNav />
    <main class="max-w-7xl mx-auto px-4 py-6">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import AppNav from '@/components/AppNav.vue'
import { useDarkMode } from '@/composables/useDarkMode'

useDarkMode()
</script>
