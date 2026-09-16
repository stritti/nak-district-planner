<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="`confirm-title-${uid}`"
      >
        <!-- Backdrop -->
        <div
          class="absolute inset-0 bg-black/40 backdrop-blur-sm"
          @click="onCancel"
        />

        <!-- Dialog panel -->
        <div
          ref="panelRef"
          class="relative w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-900"
          @keydown.escape="onCancel"
        >
          <!-- Title -->
          <h2
            :id="`confirm-title-${uid}`"
            class="text-lg font-semibold"
            :class="titleColorClass"
          >
            {{ title }}
          </h2>

          <!-- Message -->
          <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
            {{ message }}
          </p>

          <!-- Dangerous confirmation: type to confirm -->
          <div v-if="dangerous" class="mt-4">
            <label :for="`confirm-input-${uid}`" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Gib <strong class="text-red-600">{{ confirmWord }}</strong> ein, um zu bestätigen:
            </label>
            <input
              :id="`confirm-input-${uid}`"
              v-model="typedWord"
              type="text"
              class="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
              :placeholder="confirmWord"
              @keydown.enter="onConfirm"
            />
          </div>

          <!-- Buttons -->
          <div class="mt-6 flex justify-end gap-3">
            <button
              ref="cancelBtnRef"
              class="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
              @click="onCancel"
            >
              {{ cancelText }}
            </button>
            <button
              class="rounded-md px-4 py-2 text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50"
              :class="confirmButtonClass"
              :disabled="loading || (dangerous ? typedWord !== confirmWord : false)"
              @click="onConfirm"
            >
              <span v-if="loading" class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              <span v-else>{{ confirmText }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    message: string
    confirmText?: string
    cancelText?: string
    variant?: 'danger' | 'warning' | 'info'
    loading?: boolean
    dangerous?: boolean
  }>(),
  {
    confirmText: 'Bestätigen',
    cancelText: 'Abbrechen',
    variant: 'info',
    loading: false,
    dangerous: false,
  },
)

const emit = defineEmits<{
  confirm: []
  cancel: []
}>()

const uid = computed(() => `cd-${(Math.random() * 1e9).toFixed(0)}`)
const confirmWord = computed(() => {
  switch (props.variant) {
    case 'danger':
      return 'LÖSCHEN'
    case 'warning':
      return 'BESTÄTIGEN'
    default:
      return 'BESTÄTIGEN'
  }
})

const typedWord = ref('')
const panelRef = ref<HTMLElement | null>(null)
const cancelBtnRef = ref<HTMLElement | null>(null)

// Reset input and focus when dialog opens
watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      typedWord.value = ''
      await nextTick()
      if (!props.dangerous) {
        cancelBtnRef.value?.focus()
      } else {
        // Focus the input for dangerous confirmations
        const input = panelRef.value?.querySelector('input')
        input?.focus()
      }
    }
  },
)

const titleColorClass = computed(() => {
  switch (props.variant) {
    case 'danger':
      return 'text-red-700 dark:text-red-400'
    case 'warning':
      return 'text-amber-700 dark:text-amber-400'
    case 'info':
    default:
      return 'text-blue-700 dark:text-blue-400'
  }
})

const confirmButtonClass = computed(() => {
  switch (props.variant) {
    case 'danger':
      return 'bg-red-600 hover:bg-red-700 focus:ring-red-500'
    case 'warning':
      return 'bg-amber-600 hover:bg-amber-700 focus:ring-amber-500'
    case 'info':
    default:
      return 'bg-blue-600 hover:bg-blue-700 focus:ring-blue-500'
  }
})

function onConfirm() {
  if (props.loading) return
  if (props.dangerous && typedWord.value !== confirmWord.value) return
  emit('confirm')
}

function onCancel() {
  emit('cancel')
}
</script>

<style scoped>
.dialog-enter-active {
  transition: opacity 0.2s ease-out;
}
.dialog-enter-active > div:last-child {
  transition: transform 0.2s ease-out, opacity 0.2s ease-out;
}
.dialog-leave-active {
  transition: opacity 0.15s ease-in;
}
.dialog-leave-active > div:last-child {
  transition: transform 0.15s ease-in, opacity 0.15s ease-in;
}
.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}
.dialog-enter-from > div:last-child {
  transform: scale(0.95);
  opacity: 0;
}
.dialog-leave-to > div:last-child {
  transform: scale(0.95);
  opacity: 0;
}
</style>
