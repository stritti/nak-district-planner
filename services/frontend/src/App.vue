<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-950">
    <AppNav />
    <div
      v-if="authStore.isAuthenticated && authStore.accessStatus === 'PENDING_APPROVAL'"
      class="max-w-7xl mx-auto px-4 pt-4"
    >
      <div class="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        Freigabe ausstehend: Ihr Konto ist angemeldet, aber noch keinem Bezirk oder keiner Gemeinde zugeordnet.
      </div>
    </div>
    <main :class="mainClass">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppNav from './components/AppNav.vue'
import { useOIDC } from './composables/useOIDC'
import { useAuthStore } from './stores/auth'

// Get router instance in component context (safe for inject)
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const mainClass = computed(() => {
  if (route.name === 'matrix') {
    return 'w-full px-2 py-4 sm:px-3 lg:px-4'
  }
  return 'max-w-7xl mx-auto px-4 py-6'
})

const oidc = useOIDC(router)

// Restore token from persisted store
onMounted(() => {
  oidc.initialize()
})
</script>
