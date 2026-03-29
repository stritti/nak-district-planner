<template>
  <nav class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4">
      <div class="flex items-center h-14 gap-1">
        <span class="font-semibold text-gray-900 dark:text-gray-100 text-sm tracking-tight mr-4">NAK Bezirksplaner</span>
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          active-class="text-blue-600 dark:text-blue-400 font-medium bg-blue-50 dark:bg-blue-900/30 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-600 dark:hover:text-blue-400"
        >
          <component :is="link.icon" class="h-4 w-4 shrink-0" />
          {{ link.label }}
        </RouterLink>

        <div class="ml-auto">
          <button
            class="btn-icon p-2 rounded-md hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
            :title="isDark ? 'Light Mode aktivieren' : 'Dark Mode aktivieren'"
            @click="toggle"
          >
            <SunIcon v-if="isDark" class="h-4 w-4" />
            <MoonIcon v-else class="h-4 w-4" />
          </button>
        </div>
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
  MoonIcon,
  SunIcon,
  TableCellsIcon,
  UsersIcon,
} from '@heroicons/vue/24/outline'
import { useDarkMode } from '@/composables/useDarkMode'

const { isDark, toggle } = useDarkMode()

const links = [
  { to: '/events',          label: 'Ereignisse',        icon: CalendarDaysIcon },
  { to: '/matrix',          label: 'Dienstplan-Matrix', icon: TableCellsIcon },
  { to: '/admin/districts', label: 'Bezirke & Gemeinden', icon: BuildingLibraryIcon },
  { to: '/admin/leaders',   label: 'Amtstragende',      icon: UsersIcon },
  { to: '/admin/calendars', label: 'Kalender',          icon: ArrowDownTrayIcon },
  { to: '/admin/export',    label: 'Export',            icon: LinkIcon },
]
</script>
