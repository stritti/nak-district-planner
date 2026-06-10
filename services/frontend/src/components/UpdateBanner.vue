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
              v-if="store.updateMode === 'docker-socket'"
              :disabled="store.updating"
              class="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              @click="handleUpdate"
            >
              <ArrowPathIcon v-if="store.updating" class="h-4 w-4 animate-spin" />
              <ArrowDownTrayIcon v-else class="h-4 w-4" />
              {{ store.updating ? 'Update läuft...' : 'Aktualisieren' }}
            </button>
            <button
              v-else
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
              SSH auf dem Server ausführen:
            </p>
            <pre class="text-xs text-blue-800 dark:text-blue-200 overflow-x-auto whitespace-pre-wrap font-mono">
cd /opt/nak-district-planner
docker compose pull
docker compose up -d
docker compose exec backend alembic upgrade head</pre>
          </div>
        </div>

        <!-- Update result feedback -->
        <div v-if="updateFeedback" class="mt-2 pb-1">
          <div
            class="rounded-md px-4 py-2 text-sm"
            :class="updateFeedback.type === 'success'
              ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300'
              : 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300'"
          >
            <p class="font-medium">{{ updateFeedback.title }}</p>
            <p v-if="updateFeedback.message" class="text-xs mt-0.5">{{ updateFeedback.message }}</p>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useVersionStore } from '../stores/version'
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  CodeBracketIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

const authStore = useAuthStore()
const store = useVersionStore()

const showInstructions = ref(false)

interface Feedback {
  type: 'success' | 'error'
  title: string
  message?: string
}

const updateFeedback = ref<Feedback | null>(null)

const visible = computed(() => {
  return authStore.isAuthenticated && store.hasUpdate && !store.updating
})

let pollInterval: ReturnType<typeof setInterval> | null = null

async function handleUpdate() {
  updateFeedback.value = null
  try {
    const result = await store.trigger()
    if (result.status === 'started') {
      updateFeedback.value = {
        type: 'success',
        title: 'Update gestartet',
        message: 'Die Docker-Images werden aktualisiert und die Dienste neu gestartet. Dies kann einige Minuten dauern.',
      }
    } else if (result.status === 'manual') {
      showInstructions.value = true
    }
  } catch {
    updateFeedback.value = {
      type: 'error',
      title: 'Update fehlgeschlagen',
      message: 'Das Update konnte nicht gestartet werden. Bitte führen Sie die manuelle Anleitung aus.',
    }
  }
}

onMounted(() => {
  // Check version on mount (only for admins — determined by auth permissions)
  store.checkVersion()

  // Poll every 30 minutes
  pollInterval = setInterval(() => {
    store.checkVersion()
  }, 30 * 60 * 1000)
})

onUnmounted(() => {
  if (pollInterval) {
    clearInterval(pollInterval)
  }
})
</script>
