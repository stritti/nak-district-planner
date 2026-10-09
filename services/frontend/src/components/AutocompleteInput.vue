<template>
  <div class="relative">
    <input
      ref="inputRef"
      :value="inputText"
      :disabled="disabled"
      type="text"
      :placeholder="placeholder"
      autocomplete="off"
      role="combobox"
      :aria-expanded="showDropdown && flatFiltered.length > 0"
      aria-haspopup="listbox"
      aria-autocomplete="list"
      class="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      @input="onInput"
      @focus="onFocus"
      @blur="onBlur"
      @keydown.down.prevent="moveHighlight(1)"
      @keydown.up.prevent="moveHighlight(-1)"
      @keydown.enter.prevent="confirmHighlighted"
      @keydown.tab="onTab"
      @keydown.esc.prevent="closeDropdown"
    />
    <!-- fixed: the modal panel scrolls and would clip or push an absolutely positioned list -->
    <ul
      v-if="showDropdown && flatFiltered.length > 0"
      ref="listRef"
      role="listbox"
      class="fixed z-[60] overflow-y-auto rounded border border-gray-200 bg-white shadow-lg dark:border-gray-600 dark:bg-gray-800"
      :style="listStyle"
    >
      <template v-for="section in indexedSections" :key="section.label ?? '__default__'">
        <li
          v-if="section.label"
          class="sticky top-0 bg-gray-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400 dark:bg-gray-700 dark:text-gray-300"
          aria-hidden="true"
        >
          {{ section.label }}
        </li>
        <li
          v-for="{ item, index } in section.items"
          :key="item.id"
          role="option"
          :data-index="index"
          :aria-selected="index === highlightedIndex"
          class="flex cursor-pointer select-none items-baseline justify-between gap-2 px-2 py-1 text-xs"
          :class="index === highlightedIndex ? 'bg-blue-100 dark:bg-blue-900/40' : 'hover:bg-gray-50 dark:hover:bg-gray-700'"
          @mousedown.prevent="selectOption(item)"
          @mousemove="highlightedIndex = index"
        >
          <span class="truncate text-gray-900 dark:text-gray-100">{{ item.label }}</span>
          <span v-if="item.sublabel" class="shrink-0 text-[10px] text-gray-400 dark:text-gray-400">{{ item.sublabel }}</span>
        </li>
      </template>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'

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
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), { placeholder: '', disabled: false })
const emit = defineEmits<{
  (e: 'update:modelValue', value: AutocompleteValue): void
}>()

// Internal display text used to filter options
const inputRef = ref<HTMLInputElement | null>(null)
const inputText = ref(props.modelValue.text)
const listRef = ref<HTMLElement | null>(null)
const showDropdown = ref(false)
const highlightedIndex = ref(-1)
const listStyle = ref<Record<string, string>>({})

/** Longest the list may grow; it shrinks to the room that is actually visible. */
const MAX_LIST_PX = 176
const MIN_LIST_PX = 96
const VIEWPORT_MARGIN_PX = 8

/**
 * Pins the list to the input: below it when there is room, otherwise above,
 * with a height that fits the visible viewport.
 */
function positionList() {
  const input = inputRef.value
  if (!input) return
  const rect = input.getBoundingClientRect()
  const below = window.innerHeight - rect.bottom - VIEWPORT_MARGIN_PX
  const above = rect.top - VIEWPORT_MARGIN_PX
  const openUp = below < MIN_LIST_PX && above > below
  const room = Math.max(openUp ? above : below, 48)
  const style: Record<string, string> = {
    left: `${rect.left}px`,
    width: `${rect.width}px`,
    maxHeight: `${Math.min(MAX_LIST_PX, room)}px`,
  }
  if (openUp) style.bottom = `${window.innerHeight - rect.top + 2}px`
  else style.top = `${rect.bottom + 2}px`
  listStyle.value = style
}

watch(showDropdown, (open) => {
  if (open) {
    positionList()
    window.addEventListener('resize', positionList)
    window.addEventListener('scroll', positionList, true)
  } else {
    window.removeEventListener('resize', positionList)
    window.removeEventListener('scroll', positionList, true)
  }
})

watch(highlightedIndex, (index) => {
  if (index < 0) return
  nextTick(() => listRef.value?.querySelector(`[data-index="${index}"]`)?.scrollIntoView?.({ block: 'nearest' }))
})

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
    result.push({ label: priority.length > 0 ? 'Weitere Amtstragende' : null, items: other })
  return result
})

const flatFiltered = computed(() => sections.value.flatMap((s) => s.items))

// Reposition when the number of matches changes the list height or the page moved.
watch(
  () => flatFiltered.value.length,
  () => nextTick(positionList),
)

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

// User typed: free text (id = null) until a match is confirmed. The best match is
// pre-selected, so Enter or Tab picks it without reaching for arrow keys.
function onInput(event: Event) {
  const text = (event.target as HTMLInputElement).value
  inputText.value = text
  showDropdown.value = true
  highlightedIndex.value = text.trim() !== '' && flatFiltered.value.length > 0 ? 0 : -1
  emit('update:modelValue', { id: null, text })
}

// Tab accepts the pre-selected match and moves on; without typed text it only leaves.
function onTab() {
  if (showDropdown.value && inputText.value.trim() !== '' && highlightedIndex.value >= 0) {
    selectOption(flatFiltered.value[highlightedIndex.value])
  }
}

// Typed text that equals a known name counts as that choice.
function selectExactMatch() {
  const text = inputText.value.trim().toLowerCase()
  if (!text) return
  const exact = props.options.filter((o) => o.label.toLowerCase() === text)
  if (exact.length === 1 && props.modelValue.id !== exact[0].id) selectOption(exact[0])
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
    selectExactMatch()
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
  window.removeEventListener('resize', positionList)
  window.removeEventListener('scroll', positionList, true)
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

/** Focus the text input — call this when the parent opens the modal */
defineExpose({
  focus: () => inputRef.value?.focus(),
})
</script>
