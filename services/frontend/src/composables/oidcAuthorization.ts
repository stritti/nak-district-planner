// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import type { OIDCConfig, OIDCDiscovery, OIDCUser } from './oidcTypes'
import { generateCodeChallenge, generateCodeVerifier, generateState } from './pkce'
import { identityFromTokenExchange, isValidTokenExchangeResponse } from './oidcToken'
import { SESSION_CODE_VERIFIER_KEY, SESSION_STATE_KEY, clearLocalArtifacts } from './oidcSession'
import { getCurrentCSRFHeaders } from './useCSRF'

export interface AuthorizationDeps {
  config: OIDCConfig
  getClientId: () => string
  getDiscovery: () => OIDCDiscovery | null
  loadDiscovery: () => Promise<void>
  fetchUserInfo: (accessToken: string) => Promise<OIDCUser | null>
  onSessionInstalled: (token: unknown, user: OIDCUser | null) => void
}

export async function getAuthorizationUrl(deps: AuthorizationDeps): Promise<string> {
  await deps.loadDiscovery()
  const discovery = deps.getDiscovery()
  if (!discovery) throw new Error('Discovery not loaded')

  const codeVerifier = generateCodeVerifier()
  const codeChallenge = await generateCodeChallenge(codeVerifier)
  const state = generateState()

  sessionStorage.setItem(SESSION_CODE_VERIFIER_KEY, codeVerifier)
  sessionStorage.setItem(SESSION_STATE_KEY, state)

  const params = new URLSearchParams({
    client_id: deps.getClientId(),
    redirect_uri: deps.config.redirectUri,
    response_type: 'code',
    scope: deps.config.scope,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
    state,
  })

  return `${discovery.authorization_endpoint}?${params.toString()}`
}

export async function exchangeCodeForToken(
  deps: AuthorizationDeps,
  code: string,
): Promise<void> {
  await deps.loadDiscovery()
  if (!deps.getDiscovery()) throw new Error('Discovery not loaded')

  const codeVerifier = sessionStorage.getItem(SESSION_CODE_VERIFIER_KEY)
  if (!codeVerifier) throw new Error('Code verifier not found in session storage')

  // Send code + PKCE verifier to backend proxy; backend adds client_secret.
  const response = await fetch('/api/v1/auth/oidc/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getCurrentCSRFHeaders(),
    },
    body: JSON.stringify({
      grant_type: 'authorization_code',
      code,
      redirect_uri: deps.config.redirectUri,
      code_verifier: codeVerifier,
    }),
  })

  if (!response.ok) {
    const raw = await response.text()
    let parsed: unknown = raw
    try {
      parsed = JSON.parse(raw)
    } catch {
      // Keep the provider/backend response as plain text.
    }
    throw new Error(`Token exchange failed (${response.status}): ${JSON.stringify(parsed)}`)
  }

  const data: unknown = await response.json()
  if (!isValidTokenExchangeResponse(data)) {
    throw new Error('Token response missing or malformed access_token')
  }

  const { token: nextToken, user: derivedUser } = identityFromTokenExchange(
    data,
    { accessToken: '', idToken: '', refreshToken: undefined, expiresAt: 0 },
    null,
  )

  let nextUser: OIDCUser | null = derivedUser
  if (!nextUser?.sub) {
    nextUser = await deps.fetchUserInfo(nextToken.accessToken)
  }

  if (!nextUser?.sub) {
    throw new Error('OIDC identity missing: no sub in id_token/access_token or userinfo response')
  }

  deps.onSessionInstalled(nextToken, nextUser)
  clearLocalArtifacts()
}
