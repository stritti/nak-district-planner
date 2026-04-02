<template>
  <div class="min-h-screen bg-gray-50">
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
import { useAuthStore } from '@/stores/auth'

// Get router instance in component context (safe for inject)
const router = useRouter()

// Task 6.3: Initialize useOIDC in component context, passing router to avoid inject issues
const oidc = useOIDC(router)
const authStore = useAuthStore()

// Restore token from persisted store
onMounted(() => {
  if (authStore.token) {
    oidc.setToken(authStore.token, authStore.user)
  }
})

// Listen for token refresh events
window.addEventListener('oidc:refresh-token', async () => {
  try {
    await oidc.refreshToken()
    // Update store with refreshed token
    if (oidc.token.value) {
      authStore.setToken(oidc.token.value, oidc.user.value)
    }
  } catch (err) {
    console.error('Token refresh failed:', err)
  }
})
</script>
