import { createRouter, createWebHistory } from 'vue-router'
import EventListView from '@/views/EventListView.vue'
import MatrixView from '@/views/MatrixView.vue'
import DistrictsAdminView from '@/views/DistrictsAdminView.vue'
import LeadersAdminView from '@/views/LeadersAdminView.vue'
import CalendarIntegrationsView from '@/views/CalendarIntegrationsView.vue'
import ExportTokensView from '@/views/ExportTokensView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/events',
    },
    {
      path: '/events',
      name: 'events',
      component: EventListView,
    },
    {
      path: '/matrix',
      name: 'matrix',
      component: MatrixView,
    },
    {
      path: '/admin/districts',
      name: 'admin-districts',
      component: DistrictsAdminView,
    },
    {
      path: '/admin/leaders',
      name: 'admin-leaders',
      component: LeadersAdminView,
    },
    {
      path: '/admin/calendars',
      name: 'admin-calendars',
      component: CalendarIntegrationsView,
    },
    {
      path: '/admin/export',
      name: 'admin-export',
      component: ExportTokensView,
    },
  ],
})
