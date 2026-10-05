import { createRouter, createWebHistory, type NavigationGuardNext, type RouteLocationNormalized } from 'vue-router'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import EventListView from '../views/EventListView.vue'
import MatrixView from '../views/MatrixView.vue'
import DistrictsAdminView from '../views/DistrictsAdminView.vue'
import LeadersAdminView from '../views/LeadersAdminView.vue'
import CalendarIntegrationsView from '../views/CalendarIntegrationsView.vue'
import ExportTokensView from '../views/ExportTokensView.vue'
import ReminderConfigsView from '../views/ReminderConfigsView.vue'
import AuthCallbackView from '../views/AuthCallbackView.vue'
import LoginView from '../views/LoginView.vue'
import RegistrationView from '../views/RegistrationView.vue'
import { useOIDC } from '../composables/useOIDC'
import { useAuthStore } from '../stores/auth'

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

async function requireAuth(
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext,
) {
  try {
    const piniaInstance = getPinia()
    const authStore = useAuthStore(piniaInstance)

    if (authStore.isAuthenticated) {
      next()
      return
    }

    // The access token is memory-only. On a direct reload of a protected
    // route, rebuild it from the server-held HttpOnly refresh session before
    // deciding whether the user is logged out.
    const restored = await useOIDC(router).ensureSession()
    if (!restored || !authStore.isAuthenticated) {
      next('/login')
      return
    }

    // Rehydrate authorization facts once the bearer exists. The store handles
    // transient API failures fail-closed by resetting privileged flags.
    await authStore.refreshCurrentUserFlags()
    next()
  } catch {
    // Restore errors fail closed; protected navigation never proceeds without
    // an established in-memory session.
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
      path: '/admin/reminders',
      name: 'admin-reminders',
      component: ReminderConfigsView,
      beforeEnter: requireAuth,
    },
    {
      path: '/admin/external-candidates',
      name: 'admin-external-candidates',
      // Keep this view lazy: its API client depends on the router for auth recovery.
      // A top-level import here would therefore create router -> view -> API -> router.
      component: () => import('../views/ExternalCandidatesView.vue'),
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
