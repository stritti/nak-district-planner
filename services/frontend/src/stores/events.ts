// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { listEvents, type EventListParams, type EventResponse } from '../api/events'

const PAGE_SIZE = 50

export const useEventsStore = defineStore('events', () => {
  const items = ref<EventResponse[]>([])
  const total = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const filters = ref<EventListParams>({
    limit: PAGE_SIZE,
    offset: 0,
  })

  const currentPage = computed(() => Math.floor((filters.value.offset ?? 0) / PAGE_SIZE) + 1)
  const totalPages = computed(() => Math.ceil(total.value / PAGE_SIZE))

  async function fetch(options: { preserveRows?: boolean } = {}) {
    if (!options.preserveRows) loading.value = true
    error.value = null
    try {
      const res = await listEvents(filters.value)
      items.value = res.items
      total.value = res.total
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Fehler beim Laden'
    } finally {
      if (!options.preserveRows) loading.value = false
    }
  }

  function updateCached(saved: EventResponse) {
    items.value = items.value.map((item) => item.id === saved.id ? saved : item)
  }

  function setFilter(patch: Partial<EventListParams>) {
    filters.value = { ...filters.value, ...patch, offset: 0 }
  }

  function goToPage(page: number) {
    filters.value = { ...filters.value, offset: (page - 1) * PAGE_SIZE }
  }

  return { items, total, loading, error, filters, currentPage, totalPages, fetch, updateCached, setFilter, goToPage }
})
