<template>
  <div class="relative">
    <input
      :value="inputText"
      type="text"
      :placeholder="placeholder"
      autocomplete="off"
      role="combobox"
      :aria-expanded="showDropdown && indexedSections.flatMap((s) => s.items).length > 0"
      aria-haspopup="listbox"
      aria-autocomplete="list"
      class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @keydown.down.prevent="moveHighlight(1)"
      @keydown.up.prevent="moveHighlight(-1)"
      @keydown.enter.prevent="confirmHighlighted"
      @keydown.esc.prevent="closeDropdown"
    />
    <ul
      v-if="showDropdown && indexedSections.flatMap((s) => s.items).length > 0"
      role="listbox"
      class="absolute z-50 left-0 mt-1 w-full bg-white border border-gray-200 rounded shadow-lg max-h-56 overflow-y-auto"
    >
      <template v-for="(opt, idx) in flatFiltered" :key="opt.id">
        <li
          class="flex flex-col px-3 py-2 cursor-pointer select-none"
          :class="idx === highlightedIndex ? 'bg-blue-100' : 'hover:bg-gray-50'"
          @mousedown.prevent="selectOption(opt)"
          @mousemove="highlightedIndex = idx"
        >
          <span class="text-sm text-gray-900">{{ item.label }}</span>
          <span v-if="item.sublabel" class="text-xs text-gray-400">{{ item.sublabel }}</span>
        </li>
      </template>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'

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

// Internal display text used to filter options
const inputText = ref(props.modelValue.text)
const showDropdown = ref(false)
const highlightedIndex = ref(-1)

// Sync external modelValue → internal text when the parent resets the field (e.g. modal open)
watch(
  () => props.modelValue,
  (val) => {
    if (val.text !== inputText.value) inputText.value = val.text
  },
)

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

// Attaches a stable flat index to each option so the template avoids O(n) indexOf calls
const indexedSections = computed(() => {
  let offset = 0
  return sections.value.map((section) => ({
    label: section.label,
    items: section.items.map((item) => ({ item, index: offset++ })),
  }))
})

// Delay (ms) to allow mousedown on a dropdown option to fire before blur hides it
const BLUR_DELAY_MS = 150
let blurTimer: ReturnType<typeof setTimeout> | null = null

// User typed: always free-text (id = null)
function onInput(event: Event) {
  const text = (event.target as HTMLInputElement).value
  inputText.value = text
  highlightedIndex.value = -1
  emit('update:modelValue', { id: null, text })
}

function onFocus() {
  if (blurTimer !== null) {
    clearTimeout(blurTimer)
    blurTimer = null
  }
  showDropdown.value = true
  highlightedIndex.value = -1
}

function onBlur() {
  blurTimer = setTimeout(() => {
    showDropdown.value = false
    blurTimer = null
  }, BLUR_DELAY_MS)
}

function closeDropdown() {
  if (blurTimer !== null) {
    clearTimeout(blurTimer)
    blurTimer = null
  }
  showDropdown.value = false
  highlightedIndex.value = -1
}

onUnmounted(() => {
  if (blurTimer !== null) clearTimeout(blurTimer)
})

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

// Option picked from list: emit with the real leader id
function selectOption(opt: AutocompleteOption) {
  inputText.value = opt.label
  emit('update:modelValue', { id: opt.id, text: opt.label })
  showDropdown.value = false
  highlightedIndex.value = -1
}
</script>
