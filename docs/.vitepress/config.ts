import { defineConfig } from 'vitepress'
import { withOpenSpec } from '@stritti/vitepress-plugin-openspec'

export default defineConfig({
  withOpenSpec({
    lang: 'de-DE',
    title: 'NAK District Planner',
    description: 'Dokumentation für den Bezirksplaner der Neuapostolischen Kirche',
    themeConfig: {
      nav: [
        { text: 'Home', link: '/' },
        { text: 'Erste Schritte', link: '/getting-started' },
        { text: 'Use Cases', link: '/use-cases' },
        { text: 'Rollenkonzept', link: '/roles' }
      ],

      sidebar: [
        {
          text: 'Einführung',
          items: [
            { text: 'Erste Schritte', link: '/getting-started' },
            { text: 'Use Cases', link: '/use-cases' }
          ]
        },
        {
          text: 'Sicherheit & Berechtigungen',
          items: [
            { text: 'Rollenkonzept', link: '/roles' },
            { text: 'Authentifizierung (veraltet)', link: '/auth-keycloak' }
          ]
        }
      ],

      socialLinks: [
        { icon: 'github', link: 'https://github.com/stritti/nak-district-planner' }
      ]
    }
  })
})
