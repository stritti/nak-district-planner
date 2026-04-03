<template>
  <nav class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4">
      <div class="flex items-center h-14 gap-1 justify-between">
        <!-- Left: Logo & Navigation Links -->
        <div class="flex items-center gap-1">
          <span class="font-semibold text-gray-900 dark:text-gray-100 text-sm tracking-tight mr-4">NAK Bezirksplaner</span>
          <template v-if="authStore.isAuthenticated">
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
          </template>
        </div>

        <!-- Right: Dark mode toggle + User Menu or Login Button -->
        <div class="flex items-center gap-2">
          <!-- Dark mode toggle -->
          <button
            class="btn-icon p-2 rounded-md hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
            :title="isDark ? 'Light Mode aktivieren' : 'Dark Mode aktivieren'"
            :aria-label="isDark ? 'Light Mode aktivieren' : 'Dark Mode aktivieren'"
            :aria-pressed="isDark"
            @click="toggle"
          >
            <SunIcon v-if="isDark" class="h-4 w-4" />
            <MoonIcon v-else class="h-4 w-4" />
          </button>

          <!-- Login Button -->
          <template v-if="!authStore.isAuthenticated">
            <RouterLink
              to="/login"
              class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium transition-colors"
            >
              Anmelden
            </RouterLink>
          </template>

          <!-- User Menu with Email & Logout -->
          <template v-else>
            <div class="relative">
              <button
                @click="menuOpen = !menuOpen"
                class="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                <div class="text-right">
                  <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ authStore.user?.name || authStore.user?.email || 'Benutzer' }}
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">{{ authStore.user?.email }}</div>
                </div>
                <svg
                  class="h-4 w-4 text-gray-400 transition-transform"
                  :class="{ 'rotate-180': menuOpen }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                </svg>
              </button>

              <!-- Dropdown Menu -->
              <Transition
                enter-active-class="transition ease-out duration-100"
                enter-from-class="transform opacity-0 scale-95"
                enter-to-class="transform opacity-100 scale-100"
                leave-active-class="transition ease-in duration-75"
                leave-from-class="transform opacity-100 scale-100"
                leave-to-class="transform opacity-0 scale-95"
              >
                <div
                  v-if="menuOpen"
                  class="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-10"
                >
                  <div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                    <p class="text-sm font-medium text-gray-900 dark:text-gray-100">{{ authStore.user?.name || 'Benutzer' }}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-400">{{ authStore.user?.email }}</p>
                  </div>

                  <button
                    @click="handleLogout"
                    class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors border-t border-gray-100 dark:border-gray-700 rounded-b-lg"
                  >
                    Abmelden
                  </button>
                </div>
              </Transition>
            </div>
          </template>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
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
import { useAuthStore } from '@/stores/auth'
import { useOIDC } from '@/composables/useOIDC'

const router = useRouter()
const authStore = useAuthStore()
const oidc = useOIDC(router)
const { isDark, toggle } = useDarkMode()

const menuOpen = ref(false)

const links = [
  { to: '/events',          label: 'Ereignisse',        icon: CalendarDaysIcon },
  { to: '/matrix',          label: 'Dienstplan-Matrix', icon: TableCellsIcon },
  { to: '/admin/districts', label: 'Bezirke & Gemeinden', icon: BuildingLibraryIcon },
  { to: '/admin/leaders',   label: 'Amtstragende',      icon: UsersIcon },
  { to: '/admin/calendars', label: 'Kalender',          icon: ArrowDownTrayIcon },
  { to: '/admin/export',    label: 'Export',            icon: LinkIcon },
]

async function handleLogout() {
  menuOpen.value = false
  await oidc.logout()
  authStore.clearAuth()
  await router.push('/login')
}
</script>

