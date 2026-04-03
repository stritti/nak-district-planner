import { createApp } from 'vue'
import App from './App.vue'
import { router, getRouterPinia } from './router'
import './assets/main.css'

// Use the SAME pinia instance that router uses
// This ensures auth state is synchronized everywhere
const pinia = getRouterPinia()

const app = createApp(App)
app.use(pinia)
app.use(router)

app.mount('#app')
