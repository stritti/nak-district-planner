<template>
  <nav class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
    <div class="max-w-7xl mx-auto px-4">
      <div class="flex items-center h-14 gap-1 justify-between">
        <!-- Left: Logo & Navigation Links -->
        <div class="flex items-center gap-1 min-w-0">
          <!-- Hamburger button for mobile -->
          <button
            class="sm:hidden p-2 -ml-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
            aria-label="Navigation öffnen"
            @click.stop="mobileNavOpen = !mobileNavOpen; menuOpen = false"
          >
            <Bars3Icon class="h-5 w-5" />
          </button>

          <span class="font-semibold text-gray-900 dark:text-gray-100 text-sm tracking-tight mr-4 shrink-0">NAK Bezirksplaner</span>

          <!-- Desktop nav links (hidden on mobile) -->
          <template v-if="authStore.isAuthenticated">
            <div class="hidden sm:flex items-center gap-1">
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
            </div>
            <span
              v-if="authStore.isSuperadmin"
              class="ml-2 hidden sm:inline-flex items-center rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700"
            >
              Superadmin
            </span>
            <RouterLink
              v-if="authStore.pendingRegistrationsCount > 0"
              to="/admin/leaders"
              class="ml-2 hidden sm:inline-flex items-center gap-1 rounded-full border border-rose-300 bg-rose-50 px-2 py-0.5 text-[11px] font-semibold text-rose-700 hover:bg-rose-100"
            >
              Registrierungen offen
              <span class="inline-flex min-w-[1.1rem] items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] text-white">
                {{ authStore.pendingRegistrationsCount }}
              </span>
            </RouterLink>
          </template>
        </div>

        <!-- Right: Dark mode toggle + User Menu or Login Button -->
        <div class="flex items-center gap-2 shrink-0">
          <!-- Notification Bell (authenticated, requires selected district) -->
          <NotificationBell
            v-if="authStore.isAuthenticated && districtStore.selectedDistrictId"
            :district-id="districtStore.selectedDistrictId"
            @notification-click="handleNotificationClick"
          />

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
              class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium transition-colors whitespace-nowrap"
            >
              Anmelden
            </RouterLink>
          </template>

          <!-- User Menu with Email & Logout -->
          <template v-else>
            <div class="relative">
              <button
                @click="menuOpen = !menuOpen"
                class="flex items-center gap-2 px-2 sm:px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                <!-- Mobile: user icon only -->
                <div class="sm:hidden">
                  <UserIcon class="h-5 w-5 text-gray-500 dark:text-gray-400" />
                </div>
                <!-- Desktop: name + email -->
                <div class="text-right hidden sm:block">
                  <div class="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {{ authStore.user?.name || authStore.user?.email || 'Benutzer' }}
                  </div>
                  <div class="text-xs text-gray-500 dark:text-gray-400">{{ authStore.user?.email }}</div>
                </div>
                <svg
                  class="h-4 w-4 text-gray-400 transition-transform hidden sm:block"
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
                    <p
                      v-if="authStore.pendingRegistrationsCount > 0"
                      class="mt-2 text-xs font-medium text-rose-700"
                    >
                      {{ authStore.pendingRegistrationsCount }} ausstehende Registrierung{{ authStore.pendingRegistrationsCount === 1 ? '' : 'en' }}
                    </p>
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

    <!-- Mobile Navigation Overlay -->
    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="mobileNavOpen && authStore.isAuthenticated"
        class="fixed inset-0 z-40 bg-black/40 sm:hidden"
        @click="mobileNavOpen = false"
      />
    </Transition>

    <!-- Mobile Navigation Panel (slide-in from left) -->
    <Transition
      enter-active-class="transition-transform duration-200 ease-in-out"
      enter-from-class="-translate-x-full"
      enter-to-class="translate-x-0"
      leave-active-class="transition-transform duration-200 ease-in-out"
      leave-from-class="translate-x-0"
      leave-to-class="-translate-x-full"
    >
      <div
        v-if="mobileNavOpen && authStore.isAuthenticated"
        class="fixed inset-y-0 left-0 z-50 w-72 max-w-[80vw] bg-white dark:bg-gray-900 shadow-xl sm:hidden overflow-y-auto"
      >
        <div class="flex items-center justify-between px-4 h-14 border-b border-gray-200 dark:border-gray-700">
          <span class="font-semibold text-gray-900 dark:text-gray-100 text-sm tracking-tight">Navigation</span>
          <button
            class="p-2 rounded-md text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
            aria-label="Navigation schließen"
            @click="mobileNavOpen = false"
          >
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>

        <div class="px-3 py-3 space-y-1">
          <div
            v-if="authStore.isSuperadmin"
            class="px-3 py-2 mb-2 inline-flex items-center rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700"
          >
            Superadmin
          </div>
          <RouterLink
            v-for="link in links"
            :key="link.to"
            :to="link.to"
            class="flex items-center gap-3 px-3 py-2.5 rounded-md text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            active-class="text-blue-600 dark:text-blue-400 font-medium bg-blue-50 dark:bg-blue-900/30"
            @click="mobileNavOpen = false"
          >
            <component :is="link.icon" class="h-5 w-5 shrink-0" />
            {{ link.label }}
          </RouterLink>
        </div>

        <div
          v-if="authStore.pendingRegistrationsCount > 0"
          class="px-3 mt-2"
        >
          <RouterLink
            to="/admin/leaders"
            class="flex items-center gap-2 rounded-md border border-rose-300 bg-rose-50 dark:bg-rose-900/20 px-3 py-2.5 text-sm font-semibold text-rose-700"
            @click="mobileNavOpen = false"
          >
            Registrierungen offen
            <span class="inline-flex min-w-[1.1rem] items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] text-white">
              {{ authStore.pendingRegistrationsCount }}
            </span>
          </RouterLink>
        </div>
      </div>
    </Transition>
  </nav>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowDownTrayIcon,
  Bars3Icon,
  BuildingLibraryIcon,
  CalendarDaysIcon,
  LinkIcon,
  MoonIcon,
  SunIcon,
  TableCellsIcon,
  UserIcon,
  UsersIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { useDarkMode } from '../composables/useDarkMode'
import { useAuthStore } from '../stores/auth'
import { useDistrictsStore } from '../stores/districts'
import { useNotificationStore } from '../stores/notifications'
import { useOIDC } from '../composables/useOIDC'
import NotificationBell from './NotificationBell.vue'

const router = useRouter()
const authStore = useAuthStore()
const districtStore = useDistrictsStore()
const notificationStore = useNotificationStore()
const oidc = useOIDC(router)
const { isDark, toggle } = useDarkMode()

const menuOpen = ref(false)
const mobileNavOpen = ref(false)

// Start/stop notification polling based on auth state
watch(() => authStore.isAuthenticated, (authenticated) => {
  if (authenticated && districtStore.selectedDistrictId) {
    notificationStore.startPolling(districtStore.selectedDistrictId)
  } else {
    notificationStore.stopPolling()
  }
}, { immediate: true })

watch(() => districtStore.selectedDistrictId, (districtId) => {
  if (authStore.isAuthenticated && districtId) {
    notificationStore.startPolling(districtId)
  }
})

onUnmounted(() => {
  notificationStore.stopPolling()
})

function handleNotificationClick(notification: { id: string; type: string; payload: Record<string, unknown> }) {
  // Router navigation based on notification type can be added later
  // e.g., for type "registration": router.push('/admin/leaders')
  console.debug('Notification clicked:', notification.type, notification.payload)
}

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
  mobileNavOpen.value = false
  await oidc.logout()
  authStore.clearAuth()
  await router.push('/login')
}
</script>
