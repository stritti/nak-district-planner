import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getVersion, triggerUpdate, type SystemVersionResponse, type UpdateResponse } from '../api/system'

export const useVersionStore = defineStore('version', () => {
  const currentVersion = ref<string>('')
  const latestVersion = ref<string | null>(null)
  const lastChecked = ref<number | null>(null)
  const releaseUrl = ref<string | null>(null)
  const updateMode = ref<'manual' | 'docker-socket'>('manual')
  const loading = ref(false)
  const updating = ref(false)
  const updateResult = ref<UpdateResponse | null>(null)
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
      if (res.latest_version && res.latest_version !== res.current_version) {
        if (dismissedVersion.value !== res.latest_version) {
          hasUpdate.value = true
        }
      } else {
        hasUpdate.value = false
      }
    } catch {
      // Silently fail — version info is non-critical
      hasUpdate.value = false
    } finally {
      loading.value = false
    }
  }

  async function trigger() {
    updating.value = true
    try {
      const res: UpdateResponse = await triggerUpdate()
      updateResult.value = res
      updateMode.value = res.mode
      return res
    } catch (e) {
      updateResult.value = {
        status: 'error',
        mode: 'manual',
        instructions: null,
      }
      throw e
    } finally {
      updating.value = false
    }
  }

  function $reset() {
    currentVersion.value = ''
    latestVersion.value = null
    lastChecked.value = null
    releaseUrl.value = null
    hasUpdate.value = false
    updateResult.value = null
  }

  return {
    currentVersion,
    latestVersion,
    lastChecked,
    releaseUrl,
    updateMode,
    loading,
    updating,
    updateResult,
    dismissedVersion,
    hasUpdate,
    dismiss,
    checkVersion,
    trigger,
    $reset,
  }
})
