<template>
  <div
    v-if="hasDeviation === true"
    class="deviation-indicator-group"
    :class="{
      'deviation-indicator-group-compact': compact,
    }"
  >
    <!-- Warning icon for deviation -->
    <svg
      class="deviation-icon"
      :class="{
        'deviation-icon-compact': compact,
      }"
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
      class="deviation-tooltip"
      :class="{
        'deviation-tooltip-compact': compact,
      }"
    >
      <div class="deviation-tooltip-header">
        <strong>Abweichung von Plan</strong>
      </div>
      <div class="deviation-tooltip-content">
        <div class="deviation-row">
          <span class="deviation-label">Geplant:</span>
          <span class="deviation-value">{{ plannedTime }}</span>
        </div>
        <div class="deviation-row">
          <span class="deviation-label">Tatsächlich:</span>
          <span class="deviation-value">{{ actualTime }}</span>
        </div>
        <div
          v-if="startDiffMinutes !== null || endDiffMinutes !== null"
          class="deviation-row deviation-diff"
        >
          <span v-if="startDiffMinutes !== null" class="deviation-diff-value">
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

const props = defineProps<Props>()

const {
  hasDeviation = false,
  plannedTime = '',
  actualTime = '',
  startDiffMinutes = null,
  endDiffMinutes = null,
  compact = false,
} = props
</script>

<style scoped>
.deviation-indicator-group {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.deviation-icon {
  width: 1rem;
  height: 1rem;
  color: #d97706;
  flex-shrink: 0;
}

.deviation-icon-compact {
  width: 0.875rem;
  height: 0.875rem;
}

.deviation-tooltip {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  bottom: 100%;
  margin-bottom: 0.25rem;
  padding: 0.5rem 0.75rem;
  background-color: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 0.375rem;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
  font-size: 0.75rem;
  line-height: 1rem;
  color: #92400e;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.1s ease, visibility 0.1s ease;
  z-index: 50;
}

.deviation-tooltip-compact {
  font-size: 0.625rem;
  padding: 0.25rem 0.5rem;
}

.deviation-indicator-group:hover .deviation-tooltip {
  opacity: 1;
  visibility: visible;
}

.deviation-tooltip-header {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.deviation-tooltip-content {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.deviation-row {
  display: flex;
  gap: 0.25rem;
}

.deviation-label {
  color: #78350f;
}

.deviation-value {
  font-weight: 500;
}

.deviation-diff {
  margin-top: 0.25rem;
  padding-top: 0.25rem;
  border-top: 1px solid #f59e0b;
}

.deviation-diff-value {
  color: #ea580c;
  font-weight: 500;
}
</style>
