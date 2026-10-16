<!-- SPDX-FileCopyrightText: 2026 Stephan Strittmatter
     SPDX-License-Identifier: AGPL-3.0-only -->

<template>
<div class="table-container overflow-x-auto">
  <div v-if="loading" class="py-12 text-center text-sm text-gray-400 dark:text-gray-500">Laden…</div>
  <div v-else class="grid grid-cols-7 divide-x divide-gray-200 dark:divide-gray-700 min-w-[700px]">
    <div v-for="day in days" :key="day.iso" class="min-w-[100px]">
      <!-- Spaltenkopf -->
      <div
        class="px-2 py-2 text-center border-b border-gray-200 dark:border-gray-700 text-xs font-medium"
        :class="day.isToday ? 'bg-blue-600 text-white' : 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400'"
      >
        <div>{{ day.weekdayShort }}</div>
        <div class="text-base font-semibold" :class="day.isToday ? 'text-white' : 'text-gray-900 dark:text-gray-100'">
          {{ day.day }}
        </div>
      </div>
      <!-- Events -->
      <div class="p-1.5 space-y-1 min-h-[140px]">
        <!-- Feiertage oben im Inhaltsbereich (wie in der Monatsansicht) -->
        <template v-if="holidays[day.iso]?.length">
          <div
            v-for="name in holidays[day.iso]"
            :key="name"
            class="rounded px-1.5 py-1 text-xs leading-tight bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 font-medium"
          >{{ name }}</div>
        </template>
        <!-- Reguläre Events -->
        <template v-if="regularEvents(eventsByDate[day.iso]).length">
          <div
            v-for="event in regularEvents(eventsByDate[day.iso])"
            :key="event.id"
            class="rounded px-1.5 py-1 text-xs leading-tight cursor-pointer hover:opacity-80"
            :class="eventPillClass(event)"
            @click="emit('select', event)"
          >
            <div class="font-medium break-words">{{ event.title }}</div>
            <div class="text-[10px] opacity-70">{{ formatTime(event.start_at) }}</div>
          </div>
        </template>
        <div
          v-if="!holidays[day.iso]?.length && !regularEvents(eventsByDate[day.iso]).length"
          class="text-gray-200 dark:text-gray-700 text-xs text-center pt-4"
        >–</div>
      </div>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import type { EventResponse } from '../../api/events'
import { eventPillClass, formatTime, regularEvents, type CalendarDay } from './eventDisplay'

defineProps<{
  days: CalendarDay[]
  holidays: Record<string, string[]>
  eventsByDate: Record<string, EventResponse[]>
  loading: boolean
}>()
const emit = defineEmits<{ select: [event: EventResponse] }>()
</script>
