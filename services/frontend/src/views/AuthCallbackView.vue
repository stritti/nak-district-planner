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

const router = useRouter()
const route = useRoute()
const oidc = useOIDC(router)

const loading = ref(true)
const success = ref(false)
const error = ref<string | null>(null)

async function handleCallback() {
  try {
    loading.value = true
    error.value = null

    const providerError = route.query.error as string | undefined
    const providerErrorDescription = route.query.error_description as string | undefined
    if (providerError) {
      error.value = providerErrorDescription
        ? `${providerError}: ${providerErrorDescription}`
        : providerError
      return
    }

    // Get authorization code from URL
    const code = route.query.code as string
    const state = route.query.state as string

    console.debug('Auth Callback received:', {
      code: code ? code.substring(0, 20) + '...' : 'missing',
      state: state ? state.substring(0, 20) + '...' : 'missing',
      url: route.fullPath,
    })

    if (!code) {
      error.value = 'Kein Autorisierungscode in der Antwort gefunden'
      return
    }

    // Verify state parameter
    const storedState = sessionStorage.getItem('oidc_state')
    console.debug('State validation:', {
      received: state ? state.substring(0, 20) + '...' : 'missing',
      stored: storedState ? storedState.substring(0, 20) + '...' : 'missing',
      match: state === storedState,
    })

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

    success.value = true

    // Redirect to events page
    await new Promise((resolve) => setTimeout(resolve, 500))
    await router.push('/events')
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : 'Authentifizierung fehlgeschlagen'
    error.value = errorMsg
    console.error('Auth callback error:', errorMsg, err)
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
