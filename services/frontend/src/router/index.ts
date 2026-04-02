import { createRouter, createWebHistory, type NavigationGuardNext, type RouteLocationNormalized } from 'vue-router'
import EventListView from '@/views/EventListView.vue'
import MatrixView from '@/views/MatrixView.vue'
import DistrictsAdminView from '@/views/DistrictsAdminView.vue'
import LeadersAdminView from '@/views/LeadersAdminView.vue'
import CalendarIntegrationsView from '@/views/CalendarIntegrationsView.vue'
import ExportTokensView from '@/views/ExportTokensView.vue'
import AuthCallbackView from '@/views/AuthCallbackView.vue'
import LoginView from '@/views/LoginView.vue'
import { useAuthStore } from '@/stores/auth'

// Task 9.1: requireAuth Guard
function requireAuth(
  to: RouteLocationNormalized,
  from: RouteLocationNormalized,
  next: NavigationGuardNext
) {
  const authStore = useAuthStore()

  if (authStore.isAuthenticated) {
    next()
  } else {
    next('/login')
  }
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
  ],
})
