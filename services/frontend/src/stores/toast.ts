import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ToastMessage, ToastType } from '../types/toast'

let nextId = 1

export const useToastStore = defineStore('toast', () => {
  const messages = ref<ToastMessage[]>([])

  function addToast(msg: {
    type: ToastType
    title: string
    message?: string
    duration?: number
    action?: { label: string; onClick: () => void }
  }) {
    const id = `toast-${nextId++}`
    const duration = msg.duration ?? 5000
    const toast: ToastMessage = { id, ...msg, duration }

    messages.value.push(toast)
    if (messages.value.length > 5) {
      messages.value.shift()
    }

    if (duration > 0) {
      setTimeout(() => removeToast(id), duration)
    }
  }

  function removeToast(id: string) {
    const idx = messages.value.findIndex((m) => m.id === id)
    if (idx !== -1) {
      messages.value.splice(idx, 1)
    }
  }

  function success(title: string, message?: string) {
    addToast({ type: 'success', title, message })
  }

  function error(title: string, message?: string) {
    addToast({ type: 'error', title, message, duration: 8000 })
  }

  function warning(title: string, message?: string) {
    addToast({ type: 'warning', title, message, duration: 6000 })
  }

  function info(title: string, message?: string) {
    addToast({ type: 'info', title, message })
  }

  return { messages, addToast, removeToast, success, error, warning, info }
})
