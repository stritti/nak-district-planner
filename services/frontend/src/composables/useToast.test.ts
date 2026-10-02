import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { errorMessage, useToast } from './useToast'
import { useToastStore } from '../stores/toast'

describe('errorMessage', () => {
  it.each([
    [new Error('Netzwerkfehler'), 'Netzwerkfehler'],
    ['Klartext', 'Klartext'],
    [new Error(''), 'Fallback'],
    ['', 'Fallback'],
    [{ detail: 'x' }, 'Fallback'],
    [undefined, 'Fallback'],
  ])('maps %o to %s', (error, expected) => {
    expect(errorMessage(error, 'Fallback')).toBe(expected)
  })

  it('uses a generic default fallback', () => {
    expect(errorMessage(null)).toBe('Unbekannter Fehler')
  })
})

describe('useToast', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('forwards success, info and warning to the store', () => {
    const toast = useToast()
    toast.success('Gespeichert', 'Termin')
    toast.info('Hinweis')
    toast.warning('Achtung', 'Bitte prüfen')

    const messages = useToastStore().messages
    expect(messages.map((m) => [m.type, m.title, m.message])).toEqual([
      ['success', 'Gespeichert', 'Termin'],
      ['info', 'Hinweis', undefined],
      ['warning', 'Achtung', 'Bitte prüfen'],
    ])
  })

  it('normalises thrown values for error toasts', () => {
    const toast = useToast()
    toast.error('Speichern fehlgeschlagen', new Error('409 Konflikt'))
    toast.error('Ohne Details')

    const [withDetail, withoutDetail] = useToastStore().messages
    expect(withDetail).toMatchObject({ type: 'error', message: '409 Konflikt' })
    expect(withoutDetail!.message).toBeUndefined()
  })
})
