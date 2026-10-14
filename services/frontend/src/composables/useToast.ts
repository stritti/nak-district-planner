// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { useToastStore } from '../stores/toast'

/** Human-readable message of an unknown thrown value. */
export function errorMessage(error: unknown, fallback = 'Unbekannter Fehler'): string {
  if (error instanceof Error && error.message) return error.message
  if (typeof error === 'string' && error) return error
  return fallback
}

/**
 * Toast notifications for views and stores.
 *
 * Keeps components independent of the store API and normalises thrown values,
 * so call sites do not repeat `e instanceof Error ? e.message : …`.
 */
export function useToast() {
  const store = useToastStore()
  return {
    success: (title: string, message?: string) => store.success(title, message),
    info: (title: string, message?: string) => store.info(title, message),
    warning: (title: string, message?: string) => store.warning(title, message),
    error: (title: string, error?: unknown) =>
      store.error(title, error === undefined ? undefined : errorMessage(error)),
  }
}
