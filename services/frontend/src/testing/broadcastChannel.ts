import { vi } from 'vitest'

export const postedBroadcastMessages: unknown[] = []

export class MockBroadcastChannel {
  static instances: MockBroadcastChannel[] = []
  onmessage: ((event: MessageEvent) => void) | null = null

  constructor(public name: string) {
    MockBroadcastChannel.instances.push(this)
  }

  postMessage(message: unknown) {
    postedBroadcastMessages.push(message)
  }

  close() {}
}

export function resetBroadcastChannelMocks(): void {
  MockBroadcastChannel.instances = []
  postedBroadcastMessages.length = 0
  vi.stubGlobal('BroadcastChannel', MockBroadcastChannel)
}
