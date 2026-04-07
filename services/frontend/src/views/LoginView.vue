<template>
  <div class="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
    <div class="w-full max-w-md">
      <div class="bg-white rounded-lg shadow-lg p-8">
        <!-- Header -->
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-gray-900 mb-2">NAK District Planner</h1>
          <p class="text-gray-600">Veranstaltungsplanung für Distrikte</p>
        </div>

        <!-- Loading State -->
        <div v-if="isLoading" class="text-center py-8">
          <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p class="text-gray-600">Discovery wird geladen...</p>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p class="text-red-800">{{ error }}</p>
        </div>

        <!-- Login Form -->
        <div v-else>
          <form @submit.prevent="handleLogin" class="space-y-6">
            <button
              type="submit"
              class="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 font-medium transition-colors"
            >
              Mit Single Sign-on anmelden
            </button>
          </form>

          <!-- Additional Info -->
          <div class="mt-6 pt-6 border-t border-gray-200">
            <p class="text-sm text-gray-600 text-center">
              Sichere Authentifizierung über OIDC/OpenID Connect
            </p>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="text-center mt-6">
        <p class="text-sm text-gray-600">
          Noch kein Konto?
          <RouterLink to="/register" class="text-blue-500 hover:text-blue-600 font-medium">
            Jetzt registrieren
          </RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOIDC } from '@/composables/useOIDC'

const router = useRouter()
const oidc = useOIDC(router)

const isLoading = ref(false)
const error = ref<string | null>(null)

// Task 9.6: Loading-State during Discovery
async function handleLogin() {
  try {
    error.value = null
    isLoading.value = true

    // Get authorization URL (triggers discovery if needed)
    const authUrl = await oidc.getAuthorizationUrl()

    // Redirect to OIDC provider
    window.location.href = authUrl
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Authentifizierung fehlgeschlagen'
    console.error('Login error:', err)
  } finally {
    isLoading.value = false
  }
}

// Load discovery on mount to improve UX
async function loadDiscovery() {
  try {
    isLoading.value = true
    await oidc.loadDiscovery()
  } catch (err) {
    error.value = 'OIDC Discovery fehlgeschlagen. Bitte versuchen Sie es später.'
    console.error('Discovery error:', err)
  } finally {
    isLoading.value = false
  }
}

// Initialize
loadDiscovery()
</script>
