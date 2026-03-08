import { defineConfig } from 'vitepress'

export default defineConfig({
  lang: 'de-DE',
  title: 'NAK District Planner',
  description: 'Dokumentation für den Bezirksplaner der Neuapostolischen Kirche',

  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guide', link: '/getting-started' },
      { text: 'Use Cases', link: '/use-cases' }
    ],

    sidebar: [
      {
        text: 'Einführung',
        items: [
          { text: 'Erste Schritte', link: '/getting-started' },
          { text: 'Use Cases', link: '/use-cases' }
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/stritti/nak-district-planner' } 
    ]
  }
})
