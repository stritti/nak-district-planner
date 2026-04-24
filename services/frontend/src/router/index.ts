import { createRouter, createWebHistory, type NavigationGuardNext, type RouteLocationNormalized } from 'vue-router'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import EventListView from '@/views/EventListView.vue'
import MatrixView from '@/views/MatrixView.vue'
import DistrictsAdminView from '@/views/DistrictsAdminView.vue'
import LeadersAdminView from '@/views/LeadersAdminView.vue'
import CalendarIntegrationsView from '@/views/CalendarIntegrationsView.vue'
import ExportTokensView from '@/views/ExportTokensView.vue'
import AuthCallbackView from '@/views/AuthCallbackView.vue'
import LoginView from '@/views/LoginView.vue'
import RegistrationView from '@/views/RegistrationView.vue'
import { useAuthStore } from '@/stores/auth'

// Create a standalone pinia instance for router guards (not using the app instance)
// This allows us to access auth state during navigation without relying on component context
let pinia: ReturnType<typeof createPinia> | null = null

function getPinia() {
  if (!pinia) {
    pinia = createPinia()
    pinia.use(piniaPluginPersistedstate)
  }
  return pinia
}

function requireAuth(
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) {
  try {
    const piniaInstance = getPinia()
    const authStore = useAuthStore(piniaInstance)

    if (authStore.isAuthenticated) {
      next()
    } else {
      next('/login')
    }
  } catch (err) {
    // If pinia isn't available, redirect to login to be safe
    console.debug('Auth guard: pinia not ready, redirecting to login', err)
    next('/login')
  }
}

export function getRouterPinia() {
  return getPinia()
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/events',
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/auth/callback',
      name: 'auth-callback',
      component: AuthCallbackView,
    },
    {
      path: '/events',
      name: 'events',
      component: EventListView,
      beforeEnter: requireAuth,
    },
    {
      path: '/matrix',
      name: 'matrix',
      component: MatrixView,
      beforeEnter: requireAuth,
    },
    {
      path: '/admin/districts',
      name: 'admin-districts',
      component: DistrictsAdminView,
      beforeEnter: requireAuth,
    },
    {
      path: '/admin/leaders',
      name: 'admin-leaders',
      component: LeadersAdminView,
      beforeEnter: requireAuth,
    },
    {
      path: '/admin/calendars',
      name: 'admin-calendars',
      component: CalendarIntegrationsView,
      beforeEnter: requireAuth,
    },
    {
      path: '/admin/export',
      name: 'admin-export',
      component: ExportTokensView,
      beforeEnter: requireAuth,
    },
    {
      // Public self-registration page — no auth required
      path: '/register',
      name: 'register',
      component: RegistrationView,
    },
  ],
})
