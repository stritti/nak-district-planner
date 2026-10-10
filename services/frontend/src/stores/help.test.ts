// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { helpVisibilityKey } from '../help/preferences'
import { useAuthStore } from './auth'
import { useHelpStore } from './help'
import { usePreferencesStore } from './preferences'

function freshStores() {
  setActivePinia(createPinia())
  return {
    auth: useAuthStore(),
    help: useHelpStore(),
    preferences: usePreferencesStore(),
  }
}

function signIn(auth: ReturnType<typeof useAuthStore>, sub?: string) {
  auth.setToken(
    { accessToken: 'test', idToken: 'test', expiresAt: Date.now() / 1000 + 60 },
    sub ? { sub } : {},
  )
  auth.accessStatus = 'ACTIVE'
}

beforeEach(() => {
  localStorage.clear()
})

describe('useHelpStore', () => {
  it('persists guest help visibility and restores one context', async () => {
    const first = freshStores()
    first.help.hide('guest-login', 'login')
    first.help.hide('guest-events', 'events')

    expect(first.help.hidden).toContain(helpVisibilityKey('guest-login', 'login'))
    expect(first.help.isHidden('guest-events', 'events')).toBe(true)

    first.help.restore('login')
    expect(first.help.isHidden('guest-login', 'login')).toBe(false)
    expect(first.help.isHidden('guest-events', 'events')).toBe(true)

    const second = freshStores()
    await nextTick()
    expect(second.help.isHidden('guest-events', 'events')).toBe(true)
  })

  it('uses persisted user preferences for authenticated identities and deduplicates keys', async () => {
    const { auth, help, preferences } = freshStores()
    signIn(auth, 'alice')
    await nextTick()

    help.hide('planner-events', 'events')
    help.hide('planner-events', 'events')

    const key = helpVisibilityKey('planner-events', 'events')
    expect(help.identity).toBe('user:alice')
    expect(help.hidden).toEqual([key])
    expect(preferences.hiddenHelp('alice')).toEqual([key])

    preferences.hiddenHelpByUser = { alice: [helpVisibilityKey('planner-matrix', 'matrix')] }
    await nextTick()
    expect(help.hidden).toEqual([helpVisibilityKey('planner-matrix', 'matrix')])
  })

  it('has no writable identity when authentication has no subject', async () => {
    const { auth, help, preferences } = freshStores()
    signIn(auth)
    await nextTick()

    expect(help.identity).toBeNull()
    help.hide('planner-events', 'events')
    help.restore('events')

    expect(help.hidden).toEqual([])
    expect(preferences.hiddenHelpByUser).toEqual({})
  })

  it('preserves malformed and unrelated keys while restoring the requested context', async () => {
    const { auth, help, preferences } = freshStores()
    signIn(auth, 'alice')
    preferences.hiddenHelpByUser = {
      alice: [
        'not-json',
        JSON.stringify(['wrong-shape']),
        helpVisibilityKey('event-help', 'events'),
        helpVisibilityKey('matrix-help', 'matrix'),
      ],
    }
    await nextTick()

    help.restore('events')

    expect(help.hidden).toContain('not-json')
    expect(help.hidden).toContain(JSON.stringify(['wrong-shape']))
    expect(help.hidden).toContain(helpVisibilityKey('matrix-help', 'matrix'))
    expect(help.hidden).not.toContain(helpVisibilityKey('event-help', 'events'))
  })

  it('switches between user and guest state without leaking hidden keys', async () => {
    const { auth, help } = freshStores()
    help.hide('guest-login', 'login')
    signIn(auth, 'bob')
    await nextTick()
    expect(help.hidden).toEqual([])

    help.hide('bob-events', 'events')
    expect(help.hidden).toEqual([helpVisibilityKey('bob-events', 'events')])

    auth.clearAuth()
    await nextTick()
    expect(help.identity).toBe('guest')
    expect(help.hidden).toEqual([helpVisibilityKey('guest-login', 'login')])
  })
})
