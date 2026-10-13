<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
  <div
    v-if="hasDeviation === true"
    class="deviation-indicator-group group relative inline-flex items-center justify-center"
    :class="{
      'deviation-indicator-group-compact': compact,
    }"
  >
    <!-- Warning icon for deviation -->
    <svg
      class="deviation-icon shrink-0 text-amber-600"
      :class="compact ? 'deviation-icon-compact h-3.5 w-3.5' : 'h-4 w-4'"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke-width="1.5"
      stroke="currentColor"
    >
      <path
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
      />
    </svg>

    <!-- Tooltip with details -->
    <div
      class="deviation-tooltip invisible absolute bottom-full left-1/2 z-50 mb-1 -translate-x-1/2 whitespace-nowrap rounded-md border border-amber-500 bg-amber-100 px-3 py-2 text-xs leading-4 text-amber-900 opacity-0 shadow-sm transition-[opacity,visibility] duration-100 group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100"
      :class="{
        'deviation-tooltip-compact text-[10px] px-2 py-1': compact,
      }"
    >
      <div class="deviation-tooltip-header mb-1 font-semibold">
        <strong>Abweichung von Plan</strong>
      </div>
      <div class="deviation-tooltip-content flex flex-col gap-0.5">
        <div class="deviation-row flex gap-1">
          <span class="deviation-label text-amber-950">Geplant:</span>
          <span class="deviation-value font-medium">{{ plannedTime }}</span>
        </div>
        <div class="deviation-row">
          <span class="deviation-label">Tatsächlich:</span>
          <span class="deviation-value">{{ actualTime }}</span>
        </div>
        <div
          v-if="startDiffMinutes !== null || endDiffMinutes !== null"
          class="deviation-row deviation-diff mt-1 flex gap-1 border-t border-amber-500 pt-1"
        >
          <span v-if="startDiffMinutes !== null" class="deviation-diff-value font-medium text-orange-600">
            {{ startDiffMinutes > 0 ? '+' : '' }}{{ startDiffMinutes }} Min.
          </span>
          <span v-if="endDiffMinutes !== null" class="deviation-diff-value">
            (Ende: {{ endDiffMinutes > 0 ? '+' : '' }}{{ endDiffMinutes }} Min.)
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  hasDeviation?: boolean
  plannedTime?: string
  actualTime?: string
  startDiffMinutes?: number | null
  endDiffMinutes?: number | null
  compact?: boolean
}

const {
  hasDeviation = false,
  plannedTime = '',
  actualTime = '',
  startDiffMinutes = null,
  endDiffMinutes = null,
  compact = false,
} = defineProps<Props>()
</script>

