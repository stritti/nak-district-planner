// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { createApp } from 'vue'
import App from './App.vue'
import { router, getRouterPinia } from './router'
import { useAuthStore } from './stores/auth'
import {
  refreshAuthenticatedUserOnStartup,
  registerServiceWorkerOnLoad,
} from './appStartup'
import './assets/main.css'

const pinia = getRouterPinia()
const app = createApp(App)

app.use(pinia)
app.use(router)

refreshAuthenticatedUserOnStartup(useAuthStore(pinia))
registerServiceWorkerOnLoad(navigator, window)

app.mount('#app')
