/** Parses the payload of a JWT without verifying its signature. */
export function parseJwt(token: string): Record<string, unknown> {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return {}
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const padding = '='.repeat((4 - (base64.length % 4)) % 4)
    const binary = atob(base64 + padding)
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0))
    const payload: unknown = JSON.parse(new TextDecoder().decode(bytes))
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return {}
    return payload as Record<string, unknown>
  } catch {
    return {}
  }
}
