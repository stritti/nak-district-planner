import { vi } from 'vitest'

/**
 * Installs a fake `navigator.locks` that always grants the requested lock,
 * as if no other tab currently holds it.
 */
export function stubWebLocks(): void {
  vi.stubGlobal('navigator', {
    ...navigator,
    locks: {
      request: async (
        _name: string,
        _options: { ifAvailable: boolean },
        callback: (lock: Lock | null) => Promise<boolean>,
      ) => callback({ name: _name, mode: 'exclusive' } as Lock),
    },
  })
}

/** Removes `navigator.locks`, simulating an unsupported browser. */
export function stubNoWebLocks(): void {
  vi.stubGlobal('navigator', { ...navigator, locks: undefined })
}
