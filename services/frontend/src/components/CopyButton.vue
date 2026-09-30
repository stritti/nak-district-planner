<template>
  <span class="inline-flex items-center gap-2">
    <button
      type="button"
      :class="variant === 'icon' ? 'btn-icon shrink-0' : 'btn-primary shrink-0 px-3 py-2'"
      :title="label"
      :aria-label="label"
      @click="onCopy"
    >
      <ClipboardDocumentIcon v-if="variant === 'icon'" class="h-4 w-4" />
      <template v-else>{{ label }}</template>
    </button>
    <span role="status" aria-live="polite" class="text-xs">
      <span v-if="copied" class="text-green-600 dark:text-green-400">Kopiert!</span>
      <span v-else-if="failed" class="text-red-600 dark:text-red-400">Kopieren fehlgeschlagen</span>
    </span>
  </span>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useClipboard } from '@vueuse/core'
import { ClipboardDocumentIcon } from '@heroicons/vue/24/outline'

const props = withDefaults(
  defineProps<{
    value: string
    label?: string
    variant?: 'icon' | 'button'
  }>(),
  { label: 'Kopieren', variant: 'button' },
)

const emit = defineEmits<{ copied: [value: string]; error: [reason: unknown] }>()

const FEEDBACK_MS = 2000
// `legacy` falls back to execCommand where the Clipboard API is unavailable
// (e.g. plain-HTTP intranet deployments).
const { copy, copied } = useClipboard({ copiedDuring: FEEDBACK_MS, legacy: true })
const failed = ref(false)

async function onCopy() {
  failed.value = false
  try {
    await copy(props.value)
  } catch (reason) {
    failed.value = true
    emit('error', reason)
    return
  }
  // useClipboard is a silent no-op when no clipboard mechanism is available.
  if (copied.value) {
    emit('copied', props.value)
  } else {
    failed.value = true
    emit('error', new Error('Clipboard not supported'))
  }
}
</script>
