<template>
  <div class="relative">
    <input
      ref="inputRef"
      v-model="inputText"
      type="text"
      :placeholder="placeholder"
      autocomplete="off"
      class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      @focus="onFocus"
      @blur="onBlur"
      @keydown.down.prevent="moveHighlight(1)"
      @keydown.up.prevent="moveHighlight(-1)"
      @keydown.enter.prevent="confirmHighlighted"
      @keydown.esc.prevent="closeDropdown"
    />
    <ul
      v-if="showDropdown && flatFiltered.length > 0"
      class="absolute z-50 left-0 mt-1 w-full bg-white border border-gray-200 rounded shadow-lg max-h-56 overflow-y-auto"
    >
      <template v-for="section in sections" :key="section.label ?? '__default__'">
        <li
          v-if="section.label"
          class="px-3 py-1 text-[10px] font-semibold text-gray-400 uppercase tracking-wide bg-gray-50 sticky top-0"
        >
          {{ section.label }}
        </li>
        <li
          v-for="opt in section.items"
          :key="opt.id"
          class="flex flex-col px-3 py-2 cursor-pointer select-none"
          :class="flatFiltered.indexOf(opt) === highlightedIndex ? 'bg-blue-100' : 'hover:bg-gray-50'"
          @mousedown.prevent="selectOption(opt)"
          @mousemove="highlightedIndex = flatFiltered.indexOf(opt)"
        >
          <span class="text-sm text-gray-900">{{ opt.label }}</span>
          <span v-if="opt.sublabel" class="text-xs text-gray-400">{{ opt.sublabel }}</span>
        </li>
      </template>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

export interface AutocompleteOption {
  id: string
  label: string
  sublabel?: string
  isPriority?: boolean
}

export interface AutocompleteValue {
  /** ID of the selected known option, or null for free-text entry */
  id: string | null
  /** Display text (leader name typed or selected) */
  text: string
}

interface Props {
  options: AutocompleteOption[]
  modelValue: AutocompleteValue
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), { placeholder: '' })
const emit = defineEmits<{
  (e: 'update:modelValue', value: AutocompleteValue): void
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const inputText = ref(props.modelValue.text)
const showDropdown = ref(false)
const highlightedIndex = ref(-1)

// Sync external modelValue.text → inputText when parent changes it (e.g. modal reset)
watch(
  () => props.modelValue.text,
  (text) => {
    if (text !== inputText.value) inputText.value = text
  },
)

// Emit free-text value whenever the user types
watch(inputText, (text) => {
  emit('update:modelValue', { id: null, text })
  highlightedIndex.value = -1
})

const sections = computed(() => {
  const q = inputText.value.trim().toLowerCase()
  const matches = (o: AutocompleteOption) =>
    q === '' ||
    o.label.toLowerCase().includes(q) ||
    (o.sublabel?.toLowerCase().includes(q) ?? false)

  const priority = props.options.filter((o) => o.isPriority).filter(matches)
  const other = props.options.filter((o) => !o.isPriority).filter(matches)

  const result: { label: string | null; items: AutocompleteOption[] }[] = []
  if (priority.length > 0) result.push({ label: 'Eigene Gemeinde', items: priority })
  if (other.length > 0)
    result.push({ label: priority.length > 0 ? 'Weitere Amtsträger' : null, items: other })
  return result
})

const flatFiltered = computed(() => sections.value.flatMap((s) => s.items))

// Delay (ms) to allow mousedown on a dropdown option to fire before blur hides it
const BLUR_DELAY_MS = 150

function onFocus() {
  showDropdown.value = true
  highlightedIndex.value = -1
}

function onBlur() {
  setTimeout(() => {
    showDropdown.value = false
  }, BLUR_DELAY_MS)
}

function closeDropdown() {
  showDropdown.value = false
  highlightedIndex.value = -1
}

function moveHighlight(direction: 1 | -1) {
  if (!showDropdown.value) {
    showDropdown.value = true
    return
  }
  const len = flatFiltered.value.length
  if (len === 0) return
  highlightedIndex.value = (highlightedIndex.value + direction + len) % len
}

function confirmHighlighted() {
  if (highlightedIndex.value >= 0 && highlightedIndex.value < flatFiltered.value.length) {
    selectOption(flatFiltered.value[highlightedIndex.value])
  } else {
    closeDropdown()
  }
}

function selectOption(opt: AutocompleteOption) {
  inputText.value = opt.label
  emit('update:modelValue', { id: opt.id, text: opt.label })
  showDropdown.value = false
  highlightedIndex.value = -1
}
</script>
