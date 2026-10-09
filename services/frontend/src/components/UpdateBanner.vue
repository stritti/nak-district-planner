<template>
  <Transition
    enter-active-class="transition ease-out duration-300"
    enter-from-class="transform -translate-y-4 opacity-0"
    enter-to-class="transform translate-y-0 opacity-100"
    leave-active-class="transition ease-in duration-200"
    leave-from-class="transform translate-y-0 opacity-100"
    leave-to-class="transform -translate-y-4 opacity-0"
  >
    <div
      v-if="visible"
      data-testid="update-banner"
      class="bg-blue-50 dark:bg-blue-950 border-b border-blue-200 dark:border-blue-800"
    >
      <div class="max-w-7xl mx-auto px-4 py-2.5">
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-3 min-w-0">
            <!-- Icon -->
            <div class="hidden sm:flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
              <ArrowPathIcon class="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </div>
            <!-- Text -->
            <div class="min-w-0">
              <p class="text-sm font-medium text-blue-800 dark:text-blue-200">
                Neue Version {{ store.latestVersion }} verfügbar
                <span class="text-blue-600 dark:text-blue-400 font-normal">
                  (aktuell: {{ store.currentVersion }})
                </span>
              </p>
              <p v-if="store.releaseUrl" class="text-xs text-blue-600 dark:text-blue-400 mt-0.5">
                <a :href="store.releaseUrl" target="_blank" rel="noopener noreferrer" class="underline hover:text-blue-800 dark:hover:text-blue-300">
                  Release Notes anzeigen
                </a>
              </p>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2 shrink-0">
            <button
              data-testid="show-instructions"
              class="inline-flex items-center gap-1.5 rounded-md border border-blue-300 dark:border-blue-700 bg-white dark:bg-blue-900 px-3 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-800 transition-colors"
              @click="showInstructions = !showInstructions"
            >
              <CodeBracketIcon class="h-4 w-4" />
              Manuelle Anleitung
            </button>
            <button
              data-testid="dismiss-update"
              class="p-1.5 rounded-md text-blue-500 hover:text-blue-700 hover:bg-blue-100 dark:hover:bg-blue-800 transition-colors"
              title="Schließen"
              @click="store.dismiss()"
            >
              <XMarkIcon class="h-4 w-4" />
            </button>
          </div>
        </div>

        <!-- Manual instructions panel -->
        <div v-if="showInstructions" class="mt-2 pb-1">
          <div class="rounded-md bg-blue-100 dark:bg-blue-900/50 px-4 py-3">
            <p class="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1.5">
              Auf dem Server im Projektverzeichnis ausführen (siehe docs/production-runbook.md):
            </p>
            <pre class="text-xs text-blue-800 dark:text-blue-200 overflow-x-auto whitespace-pre-wrap font-mono">
git fetch --tags &amp;&amp; git checkout v{{ store.latestVersion }}
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml run --no-deps --rm --build migrate alembic upgrade head
docker compose -f docker-compose.yml up -d</pre>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useVersionStore } from '../stores/version'
import {
  ArrowPathIcon,
  CodeBracketIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

const authStore = useAuthStore()
const store = useVersionStore()

const showInstructions = ref(false)

const visible = computed(() => authStore.isAuthenticated && store.hasUpdate)

let pollInterval: ReturnType<typeof setInterval> | null = null

// The version endpoint requires authentication. Asking while signed out (login
// page, OIDC callback) is bound to 401, and the failed refresh that follows
// would log out and wipe the PKCE verifier of a login that is still in flight.
function checkVersionIfSignedIn(): void {
  if (authStore.isAuthenticated) store.checkVersion()
}

onMounted(() => {
  checkVersionIfSignedIn()

  // Poll every 30 minutes
  pollInterval = setInterval(checkVersionIfSignedIn, 30 * 60 * 1000)
})

// First check right after signing in.
watch(() => authStore.isAuthenticated, (signedIn) => {
  if (signedIn) store.checkVersion()
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>
