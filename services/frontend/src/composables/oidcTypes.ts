// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

export interface OIDCToken {
  accessToken: string
  idToken: string
  refreshToken?: string
  expiresAt: number
}

export interface OIDCUser {
  sub: string
  email?: string
  name?: string
  picture?: string
}

export interface OIDCDiscovery {
  authorization_endpoint: string
  token_endpoint: string
  userinfo_endpoint?: string
  revocation_endpoint?: string
  end_session_endpoint?: string
  jwks_uri?: string
  /** Added by backend proxy — the OIDC client ID for this application */
  client_id?: string
}

export interface OIDCConfig {
  redirectUri: string
  scope: string
}
