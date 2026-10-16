<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
<div class="table-container overflow-x-auto">
  <!-- Wochentag-Header -->
  <div class="grid grid-cols-7 divide-x divide-gray-200 dark:divide-gray-700 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 min-w-[560px]">
    <div
      v-for="wd in WEEKDAY_LABELS"
      :key="wd"
      class="py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400"
    >
      {{ wd }}
    </div>
  </div>

  <div v-if="loading" class="py-12 text-center text-sm text-gray-400 dark:text-gray-500">Laden…</div>
  <div v-else class="grid grid-cols-7 divide-x divide-gray-200 dark:divide-gray-700 min-w-[560px]">
    <div
      v-for="day in days"
      :key="day.iso"
      class="border-b border-gray-200 dark:border-gray-700 min-h-[100px] p-1"
      :class="day.currentMonth ? 'bg-white dark:bg-gray-900' : 'bg-gray-50 dark:bg-gray-800'"
    >
      <!-- Tagesnummer -->
      <div class="flex items-center justify-between mb-1">
        <span
          class="inline-flex items-center justify-center w-6 h-6 text-xs font-medium rounded-full"
          :class="day.isToday ? 'bg-blue-600 text-white' : day.currentMonth ? 'text-gray-800 dark:text-gray-200' : 'text-gray-400 dark:text-gray-500'"
        >
          {{ day.day }}
        </span>
      </div>

      <!-- Feiertage -->
      <template v-if="holidays[day.iso]?.length">
        <div
          v-for="name in holidays[day.iso]"
          :key="name"
          class="text-[10px] leading-tight px-1 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 font-medium mb-0.5 truncate"
        >
          {{ name }}
        </div>
      </template>

      <!-- Events (max. 3, dann "+N weitere") -->
      <template v-if="regularEvents(eventsByDate[day.iso]).length">
        <div
          v-for="event in regularEvents(eventsByDate[day.iso]).slice(0, 3)"
          :key="event.id"
          class="text-[10px] leading-tight px-1 py-0.5 rounded mb-0.5 truncate cursor-pointer hover:opacity-80"
          :class="eventPillClass(event)"
          @click="emit('select', event)"
        >
          {{ event.title }}
        </div>
        <div
          v-if="regularEvents(eventsByDate[day.iso]).length > 3"
          class="text-[10px] text-gray-400 dark:text-gray-500 px-1"
        >
          +{{ regularEvents(eventsByDate[day.iso]).length - 3 }} weitere
        </div>
      </template>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import type { EventResponse } from '../../api/events'
import { eventPillClass, regularEvents, type CalendarDay } from './eventDisplay'

defineProps<{
  days: CalendarDay[]
  holidays: Record<string, string[]>
  eventsByDate: Record<string, EventResponse[]>
  loading: boolean
}>()
const emit = defineEmits<{ select: [event: EventResponse] }>()

const WEEKDAY_LABELS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
</script>
