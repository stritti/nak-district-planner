import type { OIDCToken, OIDCUser } from './oidcTypes'
import { identityFromTokenExchange, isValidTokenExchangeResponse } from './oidcToken'
import { getCurrentCSRFHeaders } from './useCSRF'

const EMPTY_TOKEN: OIDCToken = {
  accessToken: '',
  idToken: '',
  expiresAt: 0,
}

export interface RefreshSessionRestoreDeps {
  ensureDiscovery: () => Promise<void>
  fetchUserInfo: (accessToken: string) => Promise<OIDCUser | null>
  installSession: (token: OIDCToken, user: OIDCUser) => void
}

/**
 * Rebuild an in-memory browser session from the server-held HttpOnly refresh cookie.
 * Missing/invalid sessions are treated as a normal logged-out state.
 *
 * Discovery is loaded first because its safe GET response also refreshes the
 * double-submit CSRF cookie needed by the subsequent cookie-backed POST.
 */
export async function restoreRefreshSession(
  deps: RefreshSessionRestoreDeps,
): Promise<boolean> {
  try {
    await deps.ensureDiscovery()
  } catch {
    return false
  }

  let response: Response
  try {
    response = await fetch('/api/v1/auth/oidc/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getCurrentCSRFHeaders(),
      },
      body: JSON.stringify({ grant_type: 'refresh_token' }),
    })
  } catch {
    return false
  }

  if (!response.ok) return false

  let data: unknown
  try {
    data = await response.json()
  } catch {
    return false
  }
  if (!isValidTokenExchangeResponse(data) || data.refresh_session !== true) return false

  const { token, user: derivedUser } = identityFromTokenExchange(data, EMPTY_TOKEN, null)
  let user = derivedUser
  if (!user?.sub) {
    try {
      user = await deps.fetchUserInfo(token.accessToken)
    } catch {
      return false
    }
  }
  if (!user?.sub) return false

  deps.installSession(token, user)
  return true
}
