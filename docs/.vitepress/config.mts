import { defineConfig } from 'vitepress'
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
    themeConfig: {
      nav: [
        { text: 'Home', link: '/' },
        { text: 'Doku-Map', link: '/documentation-map' },
        { text: 'Erste Schritte', link: '/getting-started' },
        { text: 'Use Cases', link: '/use-cases' },
        { text: 'Rollenkonzept', link: '/roles' },
        { text: 'Verbesserungen', link: '/improvement-proposals' },
        { text: 'Release', link: '/release-process' }
      ],

      sidebar: {
        '/': [
          {
            text: 'Einf\u00fchrung',
            items: [
              { text: 'Dokumentationslandkarte', link: '/documentation-map' },
              { text: 'Erste Schritte', link: '/getting-started' },
              { text: 'Use Cases', link: '/use-cases' },
              { text: 'Glossar', link: '/glossary' }
            ]
          },
          {
            text: 'Architektur & Standards',
            items: [
              { text: 'Architekturstatus', link: '/architecture-status' },
              { text: 'Engineering Standards', link: '/engineering-standards' },
              { text: 'Test- & Coverage-Strategie', link: '/coverage-strategy' }
            ]
          },
          {
            text: 'Sicherheit & Berechtigungen',
            items: [
              { text: 'Rollenkonzept', link: '/roles' },
              { text: 'Security Baseline', link: '/security-baseline' }
            ]
          },
          {
            text: 'Betrieb & Entwicklung',
            items: [
              { text: 'Production Runbook', link: '/production-runbook' },
              { text: 'Produktiv-Stack (Traefik + Keycloak)', link: '/production-compose' },
              { text: 'Release-Prozess', link: '/release-process' },
              { text: 'Release-Review 1.0', link: '/reviews/2026-10-07-release-1.0-review' },
              { text: 'Verbesserungsvorschl\u00e4ge', link: '/improvement-proposals' }
            ]
          }
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
