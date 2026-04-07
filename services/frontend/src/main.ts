import { createApp } from 'vue'
import App from './App.vue'
import { router, getRouterPinia } from './router'
import { useAuthStore } from './stores/auth'
import './assets/main.css'

// Use the SAME pinia instance that router uses
// This ensures auth state is synchronized everywhere
const pinia = getRouterPinia()

const app = createApp(App)
app.use(pinia)
app.use(router)

const authStore = useAuthStore(pinia)
if (authStore.isAuthenticated) {
  void authStore.refreshCurrentUserFlags().catch(() => {
    authStore.clearAuth()
  })
}

app.mount('#app')
