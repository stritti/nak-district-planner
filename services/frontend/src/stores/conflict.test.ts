// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { ConflictItem } from '../api/errors'
import { useConflictStore } from './conflict'

const conflict = (severity: ConflictItem['severity'], ruleId = severity): ConflictItem => ({
  rule_id: ruleId,
  severity,
  message: `${severity} conflict`,
  details: {},
})

describe('useConflictStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('classifies warnings separately and treats only non-PASS/non-WARN items as blocking', () => {
    const store = useConflictStore()
    store.setConflicts([conflict('PASS'), conflict('WARN'), conflict('BLOCK')])

    expect(store.warnings.map((item) => item.severity)).toEqual(['WARN'])
    expect(store.blocking.map((item) => item.severity)).toEqual(['BLOCK'])
  })

  it('tracks warning confirmation lifecycle and clears the complete dialog state', () => {
    const store = useConflictStore()
    store.setConflicts([conflict('WARN')])

    store.beginWarnConfirmation('save')
    expect(store.confirmingWarning).toBe(true)
    expect(store.pendingAction).toBe('save')

    store.cancelWarnConfirmation()
    expect(store.confirmingWarning).toBe(false)

    store.beginWarnConfirmation('confirm')
    store.clear()
    expect(store.conflicts).toEqual([])
    expect(store.pendingAction).toBeNull()
    expect(store.confirmingWarning).toBe(false)
  })
})
