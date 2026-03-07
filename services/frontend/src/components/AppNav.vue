<template>
  <nav class="bg-white border-b border-gray-200">
    <div class="max-w-7xl mx-auto px-4">
      <div class="flex items-center h-14 gap-1">
        <span class="font-semibold text-gray-900 text-sm tracking-tight mr-4">NAK Bezirksplaner</span>
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-colors"
          active-class="text-blue-600 font-medium bg-blue-50 hover:bg-blue-50 hover:text-blue-600"
        >
          <component :is="link.icon" class="h-4 w-4 shrink-0" />
          {{ link.label }}
        </RouterLink>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import {
  ArrowDownTrayIcon,
  BuildingLibraryIcon,
  CalendarDaysIcon,
  LinkIcon,
  TableCellsIcon,
} from '@heroicons/vue/24/outline'

const links = [
  { to: '/events',          label: 'Ereignisse',        icon: CalendarDaysIcon },
  { to: '/matrix',          label: 'Dienstplan-Matrix', icon: TableCellsIcon },
  { to: '/admin/districts', label: 'Bezirke & Gemeinden', icon: BuildingLibraryIcon },
  { to: '/admin/calendars', label: 'Kalender',          icon: ArrowDownTrayIcon },
  { to: '/admin/export',    label: 'Export',            icon: LinkIcon },
]
</script>
