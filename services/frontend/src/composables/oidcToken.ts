// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { OIDCToken, OIDCUser } from './oidcTypes'
import { parseJwt } from './jwt'

/** Internal, non-secret identifier for one browser refresh session. */
export const REFRESH_SESSION_COORDINATION_ID = 'server-held-refresh-session'

export interface TokenExchangeResponse {
  access_token: string
  id_token?: string
  refresh_session?: boolean
  expires_in?: number
}

/** Validates the JSON returned by the backend token-exchange endpoint. */
export function isValidTokenExchangeResponse(value: unknown): value is TokenExchangeResponse {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const response = value as Partial<TokenExchangeResponse>
  if (typeof response.access_token !== 'string' || response.access_token.length === 0) return false
  if (response.id_token !== undefined && typeof response.id_token !== 'string') return false
  if (response.refresh_session !== undefined && typeof response.refresh_session !== 'boolean') return false
  if (response.expires_in !== undefined &&
      (typeof response.expires_in !== 'number' || !Number.isFinite(response.expires_in) || response.expires_in <= 0)) {
    return false
  }
  return true
}

/** Validates an untrusted parsed token object used by tab-local refresh receipts. */
export function isValidTokenShape(value: unknown): value is OIDCToken {
  if (!value || typeof value !== 'object') return false
  const token = value as Partial<OIDCToken>
  return typeof token.accessToken === 'string' && token.accessToken.length > 0 &&
    typeof token.refreshToken === 'string' && token.refreshToken.length > 0 &&
    typeof token.idToken === 'string' &&
    typeof token.expiresAt === 'number' && Number.isFinite(token.expiresAt)
}

export interface OIDCIdentity {
  token: OIDCToken
  user: OIDCUser | null
}

/** Derives the next in-memory session identity from a token exchange response. */
export function identityFromTokenExchange(
  data: TokenExchangeResponse,
  currentToken: OIDCToken,
  currentUser: OIDCUser | null,
): OIDCIdentity {
  const claims = parseJwt(data.id_token || data.access_token)
  const token: OIDCToken = {
    accessToken: data.access_token,
    idToken: data.id_token || currentToken.idToken,
    refreshToken: data.refresh_session
      ? REFRESH_SESSION_COORDINATION_ID
      : currentToken.refreshToken,
    expiresAt: Math.floor(Date.now() / 1000) + Number(data.expires_in || 3600),
  }

  let user: OIDCUser | null = currentUser
  if (typeof claims.sub === 'string' && claims.sub.length > 0) {
    user = {
      sub: claims.sub,
      email: typeof claims.email === 'string' && claims.email ? claims.email : currentUser?.email,
      name: typeof claims.name === 'string' && claims.name ? claims.name : currentUser?.name,
      picture: typeof claims.picture === 'string' && claims.picture ? claims.picture : currentUser?.picture,
    }
  }

  return { token, user }
}
