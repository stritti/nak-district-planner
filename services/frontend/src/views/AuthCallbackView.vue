<template>
  <div class="flex items-center justify-center min-h-screen bg-gray-50">
    <div v-if="loading" class="text-center">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
      <p class="text-gray-600">Authentifizierung läuft...</p>
    </div>

    <div v-else-if="error" class="text-center max-w-md">
      <div class="text-red-600 font-semibold mb-2">Authentifizierungsfehler</div>
      <p class="text-gray-600 mb-4">{{ error }}</p>
      <button
        @click="goToLogin"
        class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
      >
        Zurück zum Login
      </button>
    </div>

    <div v-else-if="success" class="text-center">
      <div class="text-green-600 font-semibold mb-2">Erfolgreich angemeldet!</div>
      <p class="text-gray-600 mb-4">Sie werden weitergeleitet...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useOIDC } from '@/composables/useOIDC'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const oidc = useOIDC(router)
const authStore = useAuthStore()

const loading = ref(true)
const success = ref(false)
const error = ref<string | null>(null)

async function handleCallback() {
  try {
    loading.value = true
    error.value = null

    // Get authorization code from URL
    const code = route.query.code as string
    const state = route.query.state as string

    if (!code) {
      error.value = 'Kein Autorisierungscode in der Antwort gefunden'
      return
    }

    // Verify state parameter
    const storedState = sessionStorage.getItem('oidc_state')
    if (state !== storedState) {
      error.value = 'State-Parameter stimmt nicht überein'
      return
    }

    // Task 6.2: Exchange code for tokens
    await oidc.exchangeCodeForToken(code)

    if (!oidc.token.value || !oidc.user.value) {
      error.value = 'Token-Austausch fehlgeschlagen'
      return
    }

    // Task 7.2: Store in Pinia store (persistent)
    authStore.setToken(oidc.token.value, oidc.user.value)
    
    // Debug: Check if token is actually stored
    console.log('Token stored in authStore:', authStore.token)
    console.log('isAuthenticated:', authStore.isAuthenticated)

    success.value = true

    // Redirect to events page
    await new Promise((resolve) => setTimeout(resolve, 500))
    await router.push('/events')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Authentifizierung fehlgeschlagen'
  } finally {
    loading.value = false
  }
}

function goToLogin() {
  router.push('/login')
}

onMounted(() => {
  handleCallback()
})
</script>
