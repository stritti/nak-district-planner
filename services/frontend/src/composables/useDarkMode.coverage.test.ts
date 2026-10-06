import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

beforeEach(() => {
  vi.resetModules()
  localStorage.clear()
  document.documentElement.classList.remove('dark')
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('useDarkMode coverage gaps', () => {
  it('uses the light OS preference when no theme is persisted', async () => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false }))

    const { useDarkMode } = await import('./useDarkMode')

    expect(useDarkMode().isDark.value).toBe(false)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
