// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { usePreferencesStore } from './preferences'

beforeEach(() => setActivePinia(createPinia()))

describe('persisted user help preferences', () => {
  it('keeps users isolated, deduplicates keys and does not expose mutable internal arrays', () => {
    const store = usePreferencesStore()
    store.saveHiddenHelp('alice', ['a', 'a', 'b'])
    store.saveHiddenHelp('bob', ['c'])
    expect(store.hiddenHelp('alice')).toEqual(['a', 'b'])
    expect(store.hiddenHelp('bob')).toEqual(['c'])
    expect(store.hiddenHelp('unknown')).toEqual([])
    expect(store.hiddenHelpByUser).toEqual({ alice: ['a', 'b'], bob: ['c'] })
  })

  it('rejects empty identity and replaces only the targeted user preferences', () => {
    const store = usePreferencesStore()
    store.saveHiddenHelp('', ['unscoped'])
    expect(store.hiddenHelpByUser).toEqual({})
    store.saveHiddenHelp('alice', ['x'])
    store.saveHiddenHelp('bob', ['y'])
    store.saveHiddenHelp('alice', [])
    expect(store.hiddenHelp('alice')).toEqual([])
    expect(store.hiddenHelp('bob')).toEqual(['y'])
  })
})
