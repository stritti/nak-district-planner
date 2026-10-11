// SPDX-FileCopyrightText: 2026 Stephan Strittmatter
// SPDX-License-Identifier: AGPL-3.0-only

import { defineComponent, h } from 'vue'

/** Public fallback for URLs that no longer resolve to a registered route. */
export default defineComponent({
  name: 'NotFoundView',
  setup() {
    return () => h('main', {
      'data-testid': 'not-found-page',
      class: 'mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center gap-4 px-6 text-center',
    }, [
      h('h1', { class: 'text-3xl font-semibold text-gray-900 dark:text-gray-100' }, 'Seite nicht gefunden'),
      h('p', { class: 'text-gray-600 dark:text-gray-400' }, 'Die angeforderte Seite existiert nicht.'),
      h('a', {
        href: '/events',
        class: 'text-blue-700 underline hover:text-blue-800 dark:text-blue-300',
      }, 'Zur Terminübersicht'),
    ])
  },
})
