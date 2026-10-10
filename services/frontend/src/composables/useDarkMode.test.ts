// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

beforeEach(() => {
  vi.resetModules()
  localStorage.clear()
  document.documentElement.classList.remove('dark')
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false }))
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('useDarkMode', () => {
  it.each([
    ['dark', true],
    ['light', false],
  ] as const)('initializes from persisted %s preference', async (stored, expected) => {
    localStorage.setItem('nak-planer-theme', stored)
    const { useDarkMode } = await import('./useDarkMode')

    expect(useDarkMode().isDark.value).toBe(expected)
    expect(document.documentElement.classList.contains('dark')).toBe(expected)
  })

  it('toggles DOM plus storage off', async () => {
    localStorage.setItem('nak-planer-theme', 'dark')
    const { useDarkMode } = await import('./useDarkMode')
    const { isDark, toggle } = useDarkMode()

    toggle()
    await Promise.resolve()

    expect(isDark.value).toBe(false)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('nak-planer-theme')).toBe('light')
  })

  it('toggles DOM plus storage on', async () => {
    localStorage.setItem('nak-planer-theme', 'light')
    const { useDarkMode } = await import('./useDarkMode')
    const { isDark, toggle } = useDarkMode()

    toggle()
    await Promise.resolve()

    expect(isDark.value).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('nak-planer-theme')).toBe('dark')
  })

  it('falls back to the OS preference when nothing is persisted', async () => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }))

    const { useDarkMode } = await import('./useDarkMode')

    expect(useDarkMode().isDark.value).toBe(true)
  })

  it('falls back to the OS preference when storage reads fail', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementationOnce(() => {
      throw new Error('storage unavailable')
    })
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }))

    const { useDarkMode } = await import('./useDarkMode')

    expect(useDarkMode().isDark.value).toBe(true)
  })

  it('keeps toggling when storage writes fail', async () => {
    const { useDarkMode } = await import('./useDarkMode')
    const { isDark, toggle } = useDarkMode()
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota')
    })

    const before = isDark.value
    toggle()
    await Promise.resolve()

    expect(isDark.value).toBe(!before)
  })
})
