<template>
  <Teleport to="body">
    <div
      aria-live="polite"
      aria-relevant="additions removals"
      class="fixed bottom-4 right-4 z-50 flex flex-col-reverse gap-2"
    >
      <TransitionGroup name="toast">
        <div
          v-for="msg in messages"
          :key="msg.id"
          role="alert"
          class="flex w-80 flex-col overflow-hidden rounded-lg shadow-lg ring-1 ring-black/5"
          :class="bgClass(msg.type)"
        >
          <!-- Header -->
          <div class="flex items-start gap-2 px-4 pt-3">
            <!-- Icon -->
            <span class="mt-0.5 shrink-0 text-lg leading-none" aria-hidden="true">
              {{ icon(msg.type) }}
            </span>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-semibold" :class="textClass(msg.type)">
                {{ msg.title }}
              </p>
              <p
                v-if="msg.message"
                class="mt-0.5 text-sm opacity-90"
                :class="textClass(msg.type)"
              >
                {{ msg.message }}
              </p>
            </div>
            <button
              class="ml-2 shrink-0 rounded p-0.5 opacity-70 hover:opacity-100"
              :class="textClass(msg.type)"
              aria-label="Schliessen"
              @click="toastStore.removeToast(msg.id)"
            >
              <svg class="h-4 w-4" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" fill="none" />
              </svg>
            </button>
          </div>

          <!-- Action button -->
          <div v-if="msg.action" class="px-4 pb-2 pt-1">
            <button
              class="text-xs font-medium underline underline-offset-2"
              :class="actionClass(msg.type)"
              @click="msg.action!.onClick()"
            >
              {{ msg.action.label }}
            </button>
          </div>

          <!-- Progress bar -->
          <div
            v-if="msg.duration && msg.duration > 0"
            class="h-1 w-full overflow-hidden"
            :class="progressBgClass(msg.type)"
          >
            <div
              class="h-full animate-progress origin-left"
              :class="progressFgClass(msg.type)"
              :style="{ animationDuration: `${msg.duration}ms` }"
            />
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useToastStore } from '../stores/toast'
import type { ToastType } from '../types/toast'

const toastStore = useToastStore()
const messages = computed(() => toastStore.messages)

const icon = (t: ToastType): string => {
  switch (t) {
    case 'success':
      return '✓'
    case 'error':
      return '✗'
    case 'warning':
      return '!'
    case 'info':
      return 'i'
  }
}

const bgClass = (t: ToastType): string => {
  switch (t) {
    case 'success':
      return 'bg-green-50 dark:bg-green-950'
    case 'error':
      return 'bg-red-50 dark:bg-red-950'
    case 'warning':
      return 'bg-amber-50 dark:bg-amber-950'
    case 'info':
      return 'bg-blue-50 dark:bg-blue-950'
  }
}

const textClass = (t: ToastType): string => {
  switch (t) {
    case 'success':
      return 'text-green-800 dark:text-green-200'
    case 'error':
      return 'text-red-800 dark:text-red-200'
    case 'warning':
      return 'text-amber-800 dark:text-amber-200'
    case 'info':
      return 'text-blue-800 dark:text-blue-200'
  }
}

const actionClass = (t: ToastType): string => {
  switch (t) {
    case 'success':
      return 'text-green-700 hover:text-green-600 dark:text-green-300'
    case 'error':
      return 'text-red-700 hover:text-red-600 dark:text-red-300'
    case 'warning':
      return 'text-amber-700 hover:text-amber-600 dark:text-amber-300'
    case 'info':
      return 'text-blue-700 hover:text-blue-600 dark:text-blue-300'
  }
}

const progressBgClass = (t: ToastType): string => {
  switch (t) {
    case 'success':
      return 'bg-green-200 dark:bg-green-800'
    case 'error':
      return 'bg-red-200 dark:bg-red-800'
    case 'warning':
      return 'bg-amber-200 dark:bg-amber-800'
    case 'info':
      return 'bg-blue-200 dark:bg-blue-800'
  }
}

const progressFgClass = (t: ToastType): string => {
  switch (t) {
    case 'success':
      return 'bg-green-500 dark:bg-green-400'
    case 'error':
      return 'bg-red-500 dark:bg-red-400'
    case 'warning':
      return 'bg-amber-500 dark:bg-amber-400'
    case 'info':
      return 'bg-blue-500 dark:bg-blue-400'
  }
}
</script>

<style scoped>
.toast-enter-active {
  transition: all 0.3s ease-out;
}
.toast-leave-active {
  transition: all 0.2s ease-in;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(1rem);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(1rem) scale(0.95);
}

@keyframes progress {
  from {
    transform: scaleX(1);
  }
  to {
    transform: scaleX(0);
  }
}
.animate-progress {
  animation: progress linear forwards;
}
</style>
