// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, ref, type EffectScope } from 'vue'
import {
  clearSessionViewSettings, setSessionSettingsIdentity, sessionDate,
  sessionField, sessionText, useSessionViewSettings,
} from './useSessionViewSettings'

const scopes: EffectScope[] = []
const key = (view = 'matrix', user = 'alice', context = 'd1') =>
  'planner.view-settings.v1:' + JSON.stringify([user, view, context])

function bind(view = 'matrix', user = ref<string | null>('alice'), context = ref('d1')) {
  const query = ref('')
  const sort = ref<'default' | 'grouped'>('default')
  const date = ref('')
  const scope = effectScope()
  scopes.push(scope)
  scope.run(() => useSessionViewSettings(view, () => user.value, () => context.value, {
    query: sessionField(query, () => '', sessionText),
    sort: sessionField(sort, () => 'default', (value) => value === 'default' || value === 'grouped'),
    date: sessionField(date, () => '', sessionDate),
  }))
  return { query, sort, date, scope, user, context }
}

beforeEach(() => { sessionStorage.clear(); clearSessionViewSettings() })
afterEach(() => { scopes.splice(0).forEach((scope) => scope.stop()); vi.restoreAllMocks(); vi.unstubAllGlobals() })

describe('session view settings', () => {
  it('retains edits and explicit resets across remount/reload', () => {
    const first = bind()
    first.query.value = 'Gemeinde'
    first.sort.value = 'grouped'
    first.date.value = '2026-11-01'
    first.scope.stop()
    const restored = bind()
    expect(restored.query.value).toBe('Gemeinde')
    expect(restored.sort.value).toBe('grouped')
    expect(restored.date.value).toBe('2026-11-01')
    restored.query.value = ''
    restored.sort.value = 'default'
    restored.scope.stop()
    const cleared = bind()
    expect(cleared.query.value).toBe('')
    expect(cleared.sort.value).toBe('default')
  })

  it('isolates views, users and contexts and restores the previous context', () => {
    const matrix = bind()
    matrix.query.value = 'one'
    const events = bind('events')
    events.query.value = 'events'
    expect(matrix.query.value).toBe('one')
    const bob = bind('matrix', ref('bob'))
    expect(bob.query.value).toBe('')
    matrix.context.value = 'd2'
    expect(matrix.query.value).toBe('')
    matrix.query.value = 'two'
    matrix.context.value = 'd1'
    expect(matrix.query.value).toBe('one')
    matrix.context.value = 'd2'
    expect(matrix.query.value).toBe('two')
  })

  it.each(['{broken', '[]', 'null', '42'])('falls back for malformed storage: %s', (raw) => {
    sessionStorage.setItem(key(), raw)
    const state = bind()
    expect(state.query.value).toBe('')
    expect(state.sort.value).toBe('default')
    state.query.value = 'usable'
    expect(JSON.parse(sessionStorage.getItem(key())!).query).toBe('usable')
  })

  it('preserves valid fields while rejecting invalid dates and sorting', () => {
    sessionStorage.setItem(key(), JSON.stringify({ query: 'valid', sort: 'unknown', date: '2026-02-30', unknown: true }))
    const state = bind()
    expect(state.query.value).toBe('valid')
    expect(state.sort.value).toBe('default')
    expect(state.date.value).toBe('')
    expect(sessionDate('2026-02-28')).toBe(true)
    expect(sessionDate('not a date')).toBe(false)
    expect(sessionDate(42)).toBe(false)
  })

  it('clears retained and mounted state on logout without touching unrelated storage', () => {
    const state = bind()
    state.query.value = 'private'
    sessionStorage.setItem('unrelated', 'keep')
    clearSessionViewSettings()
    state.user.value = null
    expect(state.query.value).toBe('')
    expect(sessionStorage.getItem(key())).toBeNull()
    expect(sessionStorage.getItem('unrelated')).toBe('keep')
    state.query.value = 'signed out'
    expect(sessionStorage.getItem(key())).toBeNull()
  })

  it('clears settings on an identity change but keeps the same identity after reload', () => {
    setSessionSettingsIdentity('alice')
    const state = bind()
    state.query.value = 'alice'
    setSessionSettingsIdentity('alice')
    expect(state.query.value).toBe('alice')
    setSessionSettingsIdentity('bob')
    state.user.value = 'bob'
    expect(state.query.value).toBe('')
    expect(sessionStorage.getItem(key())).toBeNull()
  })

  it('starts a new independent tab with defaults', () => {
    const first = bind()
    first.query.value = 'old tab'
    first.scope.stop()
    sessionStorage.clear()
    expect(bind().query.value).toBe('')
  })

  it('remains usable when access to storage throws', () => {
    vi.stubGlobal('sessionStorage', { getItem: () => { throw new Error('denied') }, setItem: () => { throw new Error('quota') }, get length() { throw new Error('denied') } })
    const state = bind()
    state.query.value = 'usable'
    expect(state.query.value).toBe('usable')
    setSessionSettingsIdentity('alice')
    clearSessionViewSettings()
    expect(state.query.value).toBe('')
  })

  it('handles missing storage and the sessionStorage getter being blocked', () => {
    vi.stubGlobal('sessionStorage', undefined)
    const state = bind()
    state.query.value = 'usable'
    setSessionSettingsIdentity(null)
    clearSessionViewSettings()
    expect(state.query.value).toBe('')
  })

  it('does not retain settings without a context and stops writing after disposal', () => {
    const state = bind('matrix', ref('alice'), ref(''))
    state.query.value = 'unscoped'
    expect(sessionStorage.getItem(key('matrix', 'alice', ''))).toBeNull()
    state.context.value = 'd1'
    state.scope.stop()
    state.query.value = 'disposed'
    expect(sessionStorage.getItem(key())).toBeNull()
  })
})
