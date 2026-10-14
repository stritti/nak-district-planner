// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { apiFetch } from './client'

export interface SystemVersionResponse {
  current_version: string
  latest_version: string | null
  last_checked: number | null
  release_url: string | null
  /** Backend decides (SemVer precedence, prerelease policy) — never a downgrade. */
  update_available: boolean
}

export function getVersion(refresh = false): Promise<SystemVersionResponse> {
  const qs = refresh ? '?refresh=true' : ''
  return apiFetch(`/api/v1/system/version${qs}`)
}
