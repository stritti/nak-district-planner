// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getVersion, type SystemVersionResponse } from '../api/system'

export const useVersionStore = defineStore('version', () => {
  const currentVersion = ref<string>('')
  const latestVersion = ref<string | null>(null)
  const lastChecked = ref<number | null>(null)
  const releaseUrl = ref<string | null>(null)
  const loading = ref(false)
  const dismissedVersion = ref<string | null>(localStorage.getItem('dismissedVersion'))

  const hasUpdate = ref(false)

  function dismiss() {
    if (latestVersion.value) {
      dismissedVersion.value = latestVersion.value
      localStorage.setItem('dismissedVersion', latestVersion.value)
    }
    hasUpdate.value = false
  }

  async function checkVersion(refresh = false) {
    loading.value = true
    try {
      const res: SystemVersionResponse = await getVersion(refresh)
      currentVersion.value = res.current_version
      latestVersion.value = res.latest_version
      lastChecked.value = res.last_checked
      releaseUrl.value = res.release_url

      // Determine if update is available and not dismissed
      hasUpdate.value = res.update_available && dismissedVersion.value !== res.latest_version
    } catch {
      // Silently fail — version info is non-critical
      hasUpdate.value = false
    } finally {
      loading.value = false
    }
  }

  function $reset() {
    currentVersion.value = ''
    latestVersion.value = null
    lastChecked.value = null
    releaseUrl.value = null
    hasUpdate.value = false
  }

  return {
    currentVersion,
    latestVersion,
    lastChecked,
    releaseUrl,
    loading,
    dismissedVersion,
    hasUpdate,
    dismiss,
    checkVersion,
    $reset,
  }
})
