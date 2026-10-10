// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it } from 'vitest'
import { BrowserHelpPreferences, helpVisibilityKey } from './preferences'

function memoryStorage() {
  const values = new Map<string, string>()
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => { values.set(key, value) },
    values,
  }
}

describe('help preference adapter', () => {
  it('distinguishes contexts and user identities', () => {
    const storage = new BrowserHelpPreferences(memoryStorage())
    const key = helpVisibilityKey('intro', 'events')
    expect(key).not.toBe(helpVisibilityKey('intro', 'matrix'))
    expect(storage.write('user:alice', { hidden: [key, key] })).toBe(true)
    expect(storage.read('user:alice')).toEqual({ hidden: [key] })
    expect(storage.read('user:bob')).toEqual({ hidden: [] })
    expect(storage.read('guest')).toEqual({ hidden: [] })
  })
  it('ignores malformed, non-object and unexpected entries', () => {
    const raw = memoryStorage()
    const storage = new BrowserHelpPreferences(raw)
    raw.setItem('nak-help-hidden:v1:guest', '{broken')
    expect(storage.read('guest')).toEqual({ hidden: [] })
    raw.setItem('nak-help-hidden:v1:guest', 'null')
    expect(storage.read('guest')).toEqual({ hidden: [] })
    raw.setItem('nak-help-hidden:v1:guest', '{"hidden":["valid",42,null]}')
    expect(storage.read('guest')).toEqual({ hidden: ['valid'] })
    raw.setItem('nak-help-hidden:v1:guest', '{"hidden":{}}')
    expect(storage.read('guest')).toEqual({ hidden: [] })
  })
  it('does not crash if storage access is restricted', () => {
    const adapter = new BrowserHelpPreferences({
      getItem: () => { throw new Error('blocked') },
      setItem: () => { throw new Error('quota exceeded') },
    })
    expect(adapter.read('guest')).toEqual({ hidden: [] })
    expect(adapter.write('guest', { hidden: ['x'] })).toBe(false)
  })
})
