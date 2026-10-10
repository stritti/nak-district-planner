// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { strict as assert } from 'node:assert'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

for (const page of ['workflows.html', 'approval-workflow.html']) {
  const html = readFileSync(resolve('docs/.vitepress/dist', page), 'utf8')
  assert.match(html, /<svg[\s>]/i, `${page}: expected an SVG diagram`)
  assert.match(html, /vp-diagram/, `${page}: expected rendered Mermaid container`)
}

console.log('Mermaid SVG output verified.')
