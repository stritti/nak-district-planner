<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950">
    <AppNav />
    <main class="max-w-7xl mx-auto px-4 py-6">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppNav from '@/components/AppNav.vue'
import { useOIDC } from '@/composables/useOIDC'

// Get router instance in component context (safe for inject)
const router = useRouter()

// Task 6.3: Initialize useOIDC in component context, passing router to avoid inject issues
const oidc = useOIDC(router)

// Restore token from persisted store
onMounted(() => {
  oidc.initialize()
})
</script>
