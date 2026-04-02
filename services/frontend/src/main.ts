import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

import App from './App.vue'
import { router, getRouterPinia } from './router'
import { useOIDC } from './composables/useOIDC'
import { useAuthStore } from './stores/auth'
import './assets/main.css'

// Use the pinia instance from the router module to ensure consistency
const pinia = getRouterPinia()

const app = createApp(App)
app.use(pinia)
app.use(router)

// Task 6.3: Initialize useOIDC and restore auth state from store
const authStore = useAuthStore()
const oidc = useOIDC()

// Restore token from persisted store
if (authStore.token) {
  oidc.setToken(authStore.token, authStore.user)
}

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

app.mount('#app')
