// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { defineConfig } from 'vitepress'
import { diagramPlugin } from 'vitepress-plugin-mermaid-diagram'
import { withOpenSpec } from '@stritti/vitepress-plugin-openspec'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const docsDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const repoRoot = resolve(docsDir, '..')

export default defineConfig(
  withOpenSpec({
    // GitHub Pages serves this project site below /<repo>/; without the base,
    // every asset and link points to the domain root and 404s.
    base: '/nak-district-planner/',
    lang: 'de-DE',
    title: 'NAK District Planner',
    description: 'Dokumentation f\u00fcr den Bezirksplaner der Neuapostolischen Kirche',
    ignoreDeadLinks: false,
    srcExclude: ['superpowers/**'],
    // Keep existing public URLs stable while organizing Markdown sources by topic.
    rewrites: {
      'guide/workflows.md': 'workflows.md',
      'guide/getting-started.md': 'getting-started.md',
      'features/use-cases.md': 'use-cases.md',
      'features/roles.md': 'roles.md',
      'features/approval-workflow.md': 'approval-workflow.md',
      'features/invitations.md': 'invitations.md',
      'features/conflict-rules.md': 'conflict-rules.md',
      'architecture/status.md': 'architecture-status.md',
      'architecture/schema.md': 'schema.md',
      'development/engineering-standards.md': 'engineering-standards.md',
      'development/coverage-strategy.md': 'coverage-strategy.md',
      'development/performance-baseline.md': 'performance-baseline.md',
      'operations/production-runbook.md': 'production-runbook.md',
      'operations/production-compose.md': 'production-compose.md',
      'operations/release-process.md': 'release-process.md',
      'operations/deployment-migrations.md': 'deployment-migrations.md',
      'operations/membership-backfill-runbook.md': 'membership-backfill-runbook.md',
      'operations/opentelemetry.md': 'opentelemetry.md',
      'operations/congregation-grouping-rollout.md': 'congregation-grouping-rollout.md',
      'security/baseline.md': 'security-baseline.md',
      'security/rbac-coverage.md': 'rbac-coverage.md',
    },
    markdown: {
      config(md) {
        md.use(diagramPlugin)
      }
    },
    themeConfig: {
      nav: [
        { text: 'Überblick', link: '/' },
        { text: 'Abläufe', link: '/workflows' },
        { text: 'Use Cases', link: '/use-cases' },
        { text: 'Roadmap', link: '/roadmap' },
        { text: 'Entwicklung', link: '/getting-started' },
        { text: 'Betrieb', link: '/production-runbook' }
      ],

      sidebar: {
        '/': [
          { text: 'Einstieg', items: [
            { text: 'Projektüberblick', link: '/' },
            { text: 'So funktioniert es', link: '/workflows' },
            { text: 'Use Cases', link: '/use-cases' },
            { text: 'Roadmap', link: '/roadmap' }
          ] },
          { text: 'Funktionen und Zusammenarbeit', items: [
            { text: 'Rollenkonzept', link: '/roles' },
            { text: 'Freigabe-Workflow', link: '/approval-workflow' },
            { text: 'Einladungen', link: '/invitations' },
            { text: 'Konfliktregeln', link: '/conflict-rules' }
          ] },
          { text: 'Entwicklung und Architektur', items: [
            { text: 'Lokaler Einstieg', link: '/getting-started' },
            { text: 'Architekturstatus', link: '/architecture-status' },
            { text: 'Engineering Standards', link: '/engineering-standards' },
            { text: 'Tests und Coverage', link: '/coverage-strategy' }
          ] },
          { text: 'Betrieb und Sicherheit', items: [
            { text: 'Production Runbook', link: '/production-runbook' },
            { text: 'Produktiv-Stack', link: '/production-compose' },
            { text: 'Security Baseline', link: '/security-baseline' },
            { text: 'Release-Prozess', link: '/release-process' }
          ] },
          { text: 'Referenz', items: [
            { text: 'Glossar', link: '/glossary' },
            { text: 'Dokumentationslandkarte', link: '/documentation-map' },
            { text: 'Lizenzierung', link: '/licensing' },
            { text: 'Archiv und Historie', link: '/archive/' }
          ] }
        ]
      },

      socialLinks: [
        { icon: 'github', link: 'https://github.com/stritti/nak-district-planner' }
      ]
    }
  }, {
    specDir: resolve(repoRoot, 'openspec'),
    srcDir: docsDir
  })
)
