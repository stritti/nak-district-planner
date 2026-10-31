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
    markdown: {
      config(md) {
        md.use(diagramPlugin)
      }
    },
    themeConfig: {
      nav: [
        { text: 'Überblick', link: '/' },
        { text: 'Abläufe', link: '/guide/workflows' },
        { text: 'Use Cases', link: '/features/use-cases' },
        { text: 'Roadmap', link: '/roadmap' },
        { text: 'Entwicklung', link: '/guide/getting-started' },
        { text: 'Betrieb', link: '/operations/production-runbook' }
      ],

      sidebar: {
        '/': [
          { text: 'Einstieg', items: [
            { text: 'Projektüberblick', link: '/' },
            { text: 'So funktioniert es', link: '/guide/workflows' },
            { text: 'Rundgang: Demo-Bezirk', link: '/guide/demo-district' },
            { text: 'Use Cases', link: '/features/use-cases' },
            { text: 'Roadmap', link: '/roadmap' }
          ] },
          { text: 'Funktionen und Zusammenarbeit', items: [
            { text: 'Rollenkonzept', link: '/features/roles' },
            { text: 'Freigabe-Workflow', link: '/features/approval-workflow' },
            { text: 'Einladungen', link: '/features/invitations' },
            { text: 'Konfliktregeln', link: '/features/conflict-rules' }
          ] },
          { text: 'Entwicklung und Architektur', items: [
            { text: 'Lokaler Einstieg', link: '/guide/getting-started' },
            { text: 'Architekturstatus', link: '/architecture/status' },
            { text: 'Engineering Standards', link: '/development/engineering-standards' },
            { text: 'Tests und Coverage', link: '/development/coverage-strategy' }
          ] },
          { text: 'Betrieb und Sicherheit', items: [
            { text: 'Production Runbook', link: '/operations/production-runbook' },
            { text: 'Produktiv-Stack', link: '/operations/production-compose' },
            { text: 'Security Baseline', link: '/security/baseline' },
            { text: 'Release-Prozess', link: '/operations/release-process' }
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
