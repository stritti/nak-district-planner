/** Parses the payload of a JWT without verifying its signature. */
export function parseJwt(token: string): Record<string, unknown> {
  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return {}
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const padding = '='.repeat((4 - (base64.length % 4)) % 4)
    return JSON.parse(atob(base64 + padding)) as Record<string, unknown>
  } catch {
    return {}
  }
}
