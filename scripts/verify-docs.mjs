// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { strict as assert } from 'node:assert'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// Rendered VitePress pages may contain unrelated icons: assert all Mermaid blocks.
for (const [page, expectedDiagrams] of [
  ['workflows.html', 3],
  ['approval-workflow.html', 3]
]) {
  const html = readFileSync(resolve('docs/.vitepress/dist', page), 'utf8')
  const svgDiagrams = [...html.matchAll(/<div class="vp-diagram"[^>]*>\s*<div[^>]*>\s*<svg\b/gi)]
  assert.equal(
    svgDiagrams.length,
    expectedDiagrams,
    `${page}: expected ${expectedDiagrams} rendered Mermaid diagrams`
  )
  assert.doesNotMatch(html, /language-mermaid/, `${page}: Mermaid source remained unrendered`)
}

console.log('All six Mermaid diagrams rendered to SVG.')
