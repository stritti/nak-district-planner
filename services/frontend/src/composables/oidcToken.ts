import type { OIDCToken, OIDCUser } from './useOIDC'
import { parseJwt } from './jwt'

export interface TokenExchangeResponse {
  access_token: string
  id_token?: string
  refresh_token?: string
  expires_in?: number
}

/** Validates an untrusted parsed token object. */
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

/** Derives the next session identity from a token exchange response. */
export function identityFromTokenExchange(
  data: TokenExchangeResponse,
  currentToken: OIDCToken,
  currentUser: OIDCUser | null,
): OIDCIdentity {
  const claims = parseJwt(data.id_token || data.access_token)
  const token: OIDCToken = {
    accessToken: data.access_token,
    idToken: data.id_token || currentToken.idToken,
    refreshToken: data.refresh_token || currentToken.refreshToken,
    expiresAt: Math.floor(Date.now() / 1000) + Number(data.expires_in || 3600),
  }

  let user: OIDCUser | null = currentUser
  if (claims.sub) {
    user = {
      sub: claims.sub as string,
      email: (claims.email as string) || currentUser?.email,
      name: (claims.name as string) || currentUser?.name,
      picture: (claims.picture as string) || currentUser?.picture,
    }
  }

  return { token, user }
}
