// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { describe, expect, it, vi } from 'vitest'
import { useInlineCellCoordinator } from './useInlineCellCoordinator'

describe('useInlineCellCoordinator', () => {
  it('activates one cell and returns true for repeated activation', async () => {
    const state = useInlineCellCoordinator()
    const save = vi.fn().mockResolvedValue(true)
    expect(await state.activate('a', save)).toBe(true)
    expect(await state.activate('a', save)).toBe(true)
    expect(state.activeId.value).toBe('a')
    expect(save).not.toHaveBeenCalled()
  })

  it('ignores release of another cell and releases the current one', async () => {
    const state = useInlineCellCoordinator()
    await state.activate('a', vi.fn().mockResolvedValue(true))
    state.release('b')
    expect(state.activeId.value).toBe('a')
    state.release('a')
    expect(state.activeId.value).toBeNull()
    expect(await state.activate('c', vi.fn())).toBe(true)
    expect(state.activeId.value).toBe('c')
  })

  it('blocks navigation when the current editor cannot persist', async () => {
    const state = useInlineCellCoordinator()
    const fail = vi.fn().mockResolvedValue(false)
    await state.activate('dirty', fail)
    expect(await state.finish()).toBe(false)
    expect(state.activeId.value).toBe('dirty')
    expect(fail).toHaveBeenCalledOnce()
  })

  it('allows navigation only after the active draft resolves', async () => {
    const state = useInlineCellCoordinator()
    const finish = vi.fn().mockImplementation(async () => {
      state.release('dirty')
      return true
    })
    await state.activate('dirty', finish)
    expect(await state.finish()).toBe(true)
    expect(state.activeId.value).toBeNull()
    expect(await state.finish()).toBe(true)
    expect(finish).toHaveBeenCalledOnce()
  })

  it('resolves the existing draft before switching', async () => {
    const state = useInlineCellCoordinator()
    const finish = vi.fn().mockImplementation(async () => {
      state.release('a')
      return true
    })
    await state.activate('a', finish)
    expect(await state.activate('b', vi.fn())).toBe(true)
    expect(finish).toHaveBeenCalledOnce()
    expect(state.activeId.value).toBe('b')
  })

  it('preserves the previous editor after a failed save', async () => {
    const state = useInlineCellCoordinator()
    const finish = vi.fn().mockResolvedValue(false)
    await state.activate('a', finish)
    expect(await state.activate('b', vi.fn())).toBe(false)
    expect(state.activeId.value).toBe('a')
    expect(await state.activate('c', vi.fn())).toBe(false)
    expect(finish).toHaveBeenCalledTimes(2)
  })

  it('does not permit a competing activation while the pending save fails', async () => {
    const state = useInlineCellCoordinator()
    let resolve!: (value: boolean) => void
    const waiting = new Promise<boolean>((done) => { resolve = done })
    const finish = vi.fn().mockReturnValue(waiting)
    await state.activate('a', finish)
    const first = state.activate('b', vi.fn())
    const concurrent = state.activate('c', vi.fn())
    resolve(false)
    expect(await first).toBe(false)
    expect(await concurrent).toBe(false)
    expect(state.activeId.value).toBe('a')
    expect(finish).toHaveBeenCalledOnce()
  })

  it('lets only the latest concurrent activation win after a successful save', async () => {
    const state = useInlineCellCoordinator()
    let resolve!: (value: boolean) => void
    const waiting = new Promise<boolean>((done) => { resolve = done })
    await state.activate('a', vi.fn().mockReturnValue(waiting))
    const first = state.activate('b', vi.fn())
    const latest = state.activate('c', vi.fn())
    resolve(true)
    expect(await first).toBe(false)
    expect(await latest).toBe(true)
    expect(state.activeId.value).toBe('c')
  })

  it('allows recovery after a rejected pending save', async () => {
    const state = useInlineCellCoordinator()
    const finish = vi.fn()
      .mockRejectedValueOnce(new Error('Offline'))
      .mockResolvedValueOnce(true)
    await state.activate('a', finish)
    await expect(state.activate('b', vi.fn())).rejects.toThrow('Offline')
    expect(state.activeId.value).toBe('a')
    expect(await state.activate('c', vi.fn())).toBe(true)
    expect(state.activeId.value).toBe('c')
  })
})
