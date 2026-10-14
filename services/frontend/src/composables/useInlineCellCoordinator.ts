// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { ref, type Ref } from 'vue'

export interface InlineCellCoordinator {
  activeId: Ref<string | null>
  activate: (id: string, finishPrevious: () => Promise<boolean>) => Promise<boolean>
  release: (id: string) => void
  finish: () => Promise<boolean>
}

/** One active editor per overview; a failed save blocks switching to another cell. */
export function useInlineCellCoordinator(): InlineCellCoordinator {
  const activeId = ref<string | null>(null)
  let finishActive: (() => Promise<boolean>) | null = null
  let transition: Promise<boolean> | null = null
  let requestId = 0

  async function activate(id: string, finishPrevious: () => Promise<boolean>): Promise<boolean> {
    if (activeId.value === id) return true
    const mine = ++requestId
    if (transition && !(await transition)) return false
    // A newer activation supersedes this request after any asynchronous wait.
    if (mine !== requestId) return false
    if (finishActive) {
      const previous = finishActive
      transition = previous()
      try {
        if (!(await transition)) return false
        if (mine !== requestId) return false
      } finally {
        transition = null
      }
    }
    activeId.value = id
    finishActive = finishPrevious
    return true
  }

  async function finish(): Promise<boolean> {
    if (transition) return transition
    return finishActive ? finishActive() : true
  }

  function release(id: string): void {
    if (activeId.value !== id) return
    activeId.value = null
    finishActive = null
  }

  return { activeId, activate, release, finish }
}
