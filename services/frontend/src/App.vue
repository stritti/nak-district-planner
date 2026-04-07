<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950">
    <AppNav />
    <main :class="mainClass">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppNav from '@/components/AppNav.vue'
import { useOIDC } from '@/composables/useOIDC'

// Get router instance in component context (safe for inject)
const router = useRouter()
const route = useRoute()

const mainClass = computed(() => {
  if (route.name === 'matrix') {
    return 'w-full px-2 py-4 sm:px-3 lg:px-4'
  }
  return 'max-w-7xl mx-auto px-4 py-6'
})

// Task 6.3: Initialize useOIDC in component context, passing router to avoid inject issues
const oidc = useOIDC(router)

// Restore token from persisted store
onMounted(() => {
  oidc.initialize()
})
</script>
