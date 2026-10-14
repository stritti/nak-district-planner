// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { CrossTabRefreshState, RefreshChannelMessage } from './oidcRefresh'

export const ACTIVITY_REFRESH_LEAD_SECONDS = 120
export const ACTIVITY_CHECK_THROTTLE_MS = 15_000

const REFRESH_CHANNEL = 'oidc-refresh'

interface SchedulerState {
  refreshTimer: ReturnType<typeof setTimeout> | null
  transientRetryTimer: ReturnType<typeof setTimeout> | null
}

interface ActivityState {
  listenersAttached: boolean
  lastActivityCheckAt: number
}

const scheduler: SchedulerState = { refreshTimer: null, transientRetryTimer: null }
const activity: ActivityState = { listenersAttached: false, lastActivityCheckAt: 0 }
let refreshChannel: BroadcastChannel | null = null
let refreshChannelListenerAttached = false

let scheduledRefresh: (() => void) | null = null
let shouldTriggerActivityRefresh: (() => void) | null = null

/**
 * Binds the scheduler callbacks for the whole page. The scheduler is an
 * app-wide singleton, so the first binding wins and later composable
 * instances cannot rewire live timers or activity listeners.
 */
export function bindRefreshScheduler(options: {
  onScheduledRefresh: () => void
  onActivityRefresh: () => void
}): void {
  if (scheduledRefresh || shouldTriggerActivityRefresh) return
  scheduledRefresh = options.onScheduledRefresh
  shouldTriggerActivityRefresh = options.onActivityRefresh
}

export function getRefreshChannel(): BroadcastChannel | null {
  if (typeof BroadcastChannel === 'undefined') return null
  if (!refreshChannel) refreshChannel = new BroadcastChannel(REFRESH_CHANNEL)
  return refreshChannel
}

export function postRefreshMessage(message: RefreshChannelMessage): void {
  try {
    getRefreshChannel()?.postMessage(message)
  } catch {
    // BroadcastChannel failures must never break local refresh/session flow.
  }
}

export function isRefreshChannelListenerAttached(): boolean {
  return refreshChannelListenerAttached
}

export function markRefreshChannelListenerAttached(): void {
  refreshChannelListenerAttached = true
}

/**
 * Schedules a proactive token refresh before access-token expiry. Browsers
 * may throttle timers in background tabs, so activity is a second trigger.
 */
export function scheduleRefreshTimer(expiresAtSeconds: number): void {
  clearRefreshTimer()
  const nowSeconds = Date.now() / 1000
  const ttlSeconds = Math.max(expiresAtSeconds - nowSeconds, 0)
  const refreshLeadSeconds = Math.min(300, Math.max(5, Math.floor(ttlSeconds * 0.2)))
  const delay = Math.max((ttlSeconds - refreshLeadSeconds) * 1000, 1000)

  scheduler.refreshTimer = setTimeout(() => {
    scheduler.refreshTimer = null
    scheduledRefresh?.()
  }, delay)
}

export function clearRefreshTimer(): void {
  if (scheduler.refreshTimer) clearTimeout(scheduler.refreshTimer)
  scheduler.refreshTimer = null
}

export function clearTransientRetryTimer(): void {
  if (scheduler.transientRetryTimer) clearTimeout(scheduler.transientRetryTimer)
  scheduler.transientRetryTimer = null
}

export function scheduleTransientRetry(delayMs: number): void {
  clearTransientRetryTimer()
  scheduler.transientRetryTimer = setTimeout(() => {
    scheduler.transientRetryTimer = null
    scheduledRefresh?.()
  }, delayMs)
}

function handleUserActivity(): void {
  const now = Date.now()
  if (now - activity.lastActivityCheckAt < ACTIVITY_CHECK_THROTTLE_MS) return
  activity.lastActivityCheckAt = now
  shouldTriggerActivityRefresh?.()
}

/** Attach activity listeners once as a fallback for throttled browser timers. */
export function setupActivityRefresh(): void {
  if (activity.listenersAttached) return
  activity.listenersAttached = true

  const activityEvents = ['mousemove', 'keydown', 'click', 'touchstart', 'scroll']
  activityEvents.forEach((eventName) => {
    document.addEventListener(eventName, handleUserActivity, { passive: true })
  })
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') handleUserActivity()
  })
  window.addEventListener('focus', handleUserActivity)
}

/** @internal — resets module-level state; used by tests */
export function __resetSchedulerState(): void {
  clearRefreshTimer()
  clearTransientRetryTimer()
  refreshChannel?.close()
  refreshChannel = null
  refreshChannelListenerAttached = false
  activity.listenersAttached = false
  activity.lastActivityCheckAt = 0
  scheduledRefresh = null
  shouldTriggerActivityRefresh = null
}

export type { CrossTabRefreshState }
