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

// IMPORTANT: useOIDC() is a composable and must be called in a component context
// or after router/app is set up. We'll set it up in the App.vue root component instead.
// For now, just mount the app and let App.vue handle useOIDC initialization

app.mount('#app')
