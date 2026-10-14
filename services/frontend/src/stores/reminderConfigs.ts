// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  createReminderConfig,
  deleteReminderConfig,
  listReminderConfigs,
  updateReminderConfig,
  type ReminderConfig,
  type ReminderConfigInput,
} from '../api/reminderConfigs'

export const useReminderConfigsStore = defineStore('reminder-configs', () => {
  const items = ref<ReminderConfig[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const districtId = ref<string | null>(null)

  async function load(id: string) {
    districtId.value = id
    loading.value = true
    error.value = null
    items.value = []
    try {
      const result = await listReminderConfigs(id)
      if (districtId.value === id) items.value = result
    } catch (cause) {
      if (districtId.value === id) error.value = cause instanceof Error ? cause.message : 'Erinnerungen konnten nicht geladen werden'
    } finally {
      if (districtId.value === id) loading.value = false
    }
  }

  async function create(input: ReminderConfigInput) {
    if (!districtId.value) throw new Error('Kein Bezirk ausgewählt')
    const id = districtId.value
    saving.value = true
    error.value = null
    try {
      const config = await createReminderConfig(id, input)
      if (districtId.value === id) items.value.push(config)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : 'Erinnerung konnte nicht angelegt werden'
      throw cause
    } finally {
      saving.value = false
    }
  }

  async function update(configId: string, input: Partial<ReminderConfigInput>) {
    if (!districtId.value) throw new Error('Kein Bezirk ausgewählt')
    const id = districtId.value
    saving.value = true
    error.value = null
    try {
      const config = await updateReminderConfig(id, configId, input)
      if (districtId.value === id) items.value = items.value.map(item => item.id === configId ? config : item)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : 'Erinnerung konnte nicht gespeichert werden'
      throw cause
    } finally {
      saving.value = false
    }
  }

  async function deactivate(configId: string) {
    if (!districtId.value) throw new Error('Kein Bezirk ausgewählt')
    const id = districtId.value
    saving.value = true
    error.value = null
    try {
      await deleteReminderConfig(id, configId)
      if (districtId.value === id) items.value = items.value.map(item => item.id === configId ? { ...item, is_active: false } : item)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : 'Erinnerung konnte nicht deaktiviert werden'
      throw cause
    } finally {
      saving.value = false
    }
  }

  return { items, loading, saving, error, districtId, load, create, update, deactivate }
})
